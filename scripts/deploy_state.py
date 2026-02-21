#!/usr/bin/env python3
"""Управление deploy-state.md — внешняя память агента."""

import argparse
import json
import os
import re
import sys

DEFAULT_PATH = "deploy-state.md"

TEMPLATE = """# Deploy State — НЕ КОММИТИТЬ (добавлен в .gitignore)

## Проект
- Тип: {app_type}
- Рантайм: {runtime}
- Фреймворк: {framework}
- Порт: {port}

## Git
- Инициализирован: {git_init}
- Remote: {git_remote}
- Ветка: {git_branch}
- Хостинг: {git_hosting}

## Решения пользователя
- Стратегия: НЕ ВЫБРАНА
- Docker: НЕ СПРОШЕН
- Домен: НЕ СПРОШЕН
- CI/CD: НЕ СПРОШЕН

## Токены и ключи
- Timeweb API: —
- GitHub PAT: —
- SSH-ключ: —

## Инфраструктура
- Сервер ID: —
- Сервер IP: —
- БД ID: —
- БД URL: —

## Прогресс
- [x] Анализ проекта
- [ ] API-токен
- [ ] Баланс проверен
- [ ] Стратегия выбрана
- [ ] Docker решён
- [ ] Инфраструктура создана
- [ ] ПО установлено
- [ ] Проект загружен
- [ ] Приложение запущено
- [ ] Домен — НЕ СПРОШЕН
- [ ] CI/CD — НЕ СПРОШЕН
- [ ] Финальная проверка
"""


def init(path, project_data=None):
    """Создаёт начальный state-файл из данных анализа проекта."""
    data = project_data or {}
    git = data.get("git", {})
    content = TEMPLATE.format(
        app_type=data.get("app_type", "—"),
        runtime=data.get("runtime", "—"),
        framework=data.get("framework", "—") or "—",
        port=data.get("port", "—") or "—",
        git_init="да" if git.get("initialized") else "нет",
        git_remote=git.get("remote", "—") or "—",
        git_branch=git.get("branch", "—") or "—",
        git_hosting=git.get("hosting", "—") or "—",
    )
    with open(path, "w") as f:
        f.write(content)

    # Добавить в .gitignore
    gitignore = ".gitignore"
    entry = "deploy-state.md"
    if os.path.exists(gitignore):
        with open(gitignore) as f:
            if entry in f.read():
                print(json.dumps({"ok": True, "created": path, "gitignore": "already present"}))
                return
    with open(gitignore, "a") as f:
        f.write(f"\n{entry}\n")

    print(json.dumps({"ok": True, "created": path, "gitignore": "added"}))


def update(path, section, key, value):
    """Обновляет конкретное поле в state-файле. Если section указан — ищет только в этой секции."""
    if not os.path.exists(path):
        print(json.dumps({"error": f"State file not found: {path}"}))
        sys.exit(1)

    with open(path) as f:
        content = f.read()

    if section:
        # Найти секцию и заменить только внутри неё
        section_pattern = re.compile(
            rf"(## {re.escape(section)}\n)(.*?)(?=\n## |\Z)",
            re.DOTALL
        )
        section_match = section_pattern.search(content)
        if not section_match:
            print(json.dumps({"error": f"Section '{section}' not found in state file"}))
            sys.exit(1)

        section_text = section_match.group(2)
        line_pattern = re.compile(rf"(- {re.escape(key)}:\s*)(.+)")
        new_section, count = line_pattern.subn(rf"\g<1>{value}", section_text)

        if count == 0:
            print(json.dumps({"error": f"Key '{key}' not found in section '{section}'"}))
            sys.exit(1)

        new_content = content[:section_match.start(2)] + new_section + content[section_match.end(2):]
    else:
        # Без секции — заменить первое вхождение
        pattern = re.compile(rf"(- {re.escape(key)}:\s*)(.+)")
        new_content, count = pattern.subn(rf"\g<1>{value}", content, count=1)

        if count == 0:
            print(json.dumps({"error": f"Key '{key}' not found in state file"}))
            sys.exit(1)

    with open(path, "w") as f:
        f.write(new_content)

    print(json.dumps({"ok": True, "updated": key, "value": value, "section": section}))


def check_progress(path, step_name, done=True):
    """Отмечает шаг как выполненный или пропущенный."""
    if not os.path.exists(path):
        print(json.dumps({"error": f"State file not found: {path}"}))
        sys.exit(1)

    with open(path) as f:
        content = f.read()

    if done:
        # [ ] step → [x] step
        old = f"- [ ] {step_name}"
        new = f"- [x] {step_name}"
    else:
        # Пропущенный шаг
        old = f"- [ ] {step_name}"
        new = f"- [—] {step_name}"

    if old not in content:
        # Попробуем найти с " — " суффиксом
        pattern = re.compile(rf"- \[ \] {re.escape(step_name)}.*")
        match = pattern.search(content)
        if match:
            old = match.group(0)
            new = new if "НЕ СПРОШЕН" not in old else new
        else:
            print(json.dumps({"error": f"Step '{step_name}' not found"}))
            sys.exit(1)

    content = content.replace(old, new, 1)
    with open(path, "w") as f:
        f.write(content)

    print(json.dumps({"ok": True, "step": step_name, "done": done}))


def verify(path):
    """Проверяет, все ли шаги завершены. Показывает незавершённые."""
    if not os.path.exists(path):
        print(json.dumps({"error": f"State file not found: {path}"}))
        sys.exit(1)

    with open(path) as f:
        content = f.read()

    incomplete = []
    for m in re.finditer(r"- \[ \] (.+)", content):
        incomplete.append(m.group(1))

    not_asked = []
    for m in re.finditer(r"НЕ СПРОШЕН", content):
        # Найти ключ
        line_start = content.rfind("\n", 0, m.start()) + 1
        line = content[line_start:content.find("\n", m.start())]
        not_asked.append(line.strip())

    all_done = len(incomplete) == 0 and len(not_asked) == 0
    print(json.dumps({
        "all_done": all_done,
        "incomplete_steps": incomplete,
        "not_asked": not_asked,
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Manage deploy-state.md")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("init")
    p.add_argument("--path", default=DEFAULT_PATH)
    p.add_argument("--project-json", help="JSON output from analyze_project.py")

    p = sub.add_parser("update")
    p.add_argument("--path", default=DEFAULT_PATH)
    p.add_argument("--section", help="Section name, e.g. 'Решения пользователя'")
    p.add_argument("--key", required=True, help="Field name, e.g. 'Стратегия'")
    p.add_argument("--value", required=True)

    p = sub.add_parser("check")
    p.add_argument("--path", default=DEFAULT_PATH)
    p.add_argument("--step", required=True, help="Step name from progress list")
    p.add_argument("--skip", action="store_true", help="Mark as skipped instead of done")

    p = sub.add_parser("verify")
    p.add_argument("--path", default=DEFAULT_PATH)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        project_data = None
        if args.project_json:
            project_data = json.loads(args.project_json)
        init(args.path, project_data)
    elif args.command == "update":
        update(args.path, getattr(args, 'section', None), args.key, args.value)
    elif args.command == "check":
        check_progress(args.path, args.step, done=not args.skip)
    elif args.command == "verify":
        verify(args.path)


if __name__ == "__main__":
    main()
