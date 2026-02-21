#!/usr/bin/env python3
"""Анализ проекта: тип, фреймворк, порт, env, Docker, Git."""

import argparse
import json
import os
import re
import subprocess
import sys


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def read_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def detect_runtime(project_dir):
    """Определяет язык/рантайм по файлам-манифестам."""
    # Bun: проверяем lock-файл ДО package.json (Bun-проекты тоже имеют package.json)
    if os.path.exists(os.path.join(project_dir, "bun.lockb")) or \
       os.path.exists(os.path.join(project_dir, "bunfig.toml")):
        return "bun"

    # Deno
    if os.path.exists(os.path.join(project_dir, "deno.json")) or \
       os.path.exists(os.path.join(project_dir, "deno.jsonc")):
        return "deno"

    checks = [
        ("package.json", "nodejs"),
        ("requirements.txt", "python"),
        ("pyproject.toml", "python"),
        ("Pipfile", "python"),
        ("go.mod", "go"),
        ("composer.json", "php"),
        ("Gemfile", "ruby"),
        ("pom.xml", "java"),
        ("build.gradle", "java"),
        ("Cargo.toml", "rust"),
        ("mix.exs", "elixir"),
    ]
    for filename, runtime in checks:
        if os.path.exists(os.path.join(project_dir, filename)):
            return runtime
    return "unknown"


def detect_package_manager(project_dir):
    """Определяет менеджер пакетов по lock-файлу."""
    checks = [
        ("bun.lockb", "bun"),
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
    ]
    for filename, manager in checks:
        if os.path.exists(os.path.join(project_dir, filename)):
            return manager

    # Фолбэк: если есть package.json — npm
    if os.path.exists(os.path.join(project_dir, "package.json")):
        return "npm"
    return None


def detect_runtime_version(project_dir, runtime):
    """Определяет версию рантайма из конфигурационных файлов."""
    if runtime in ("nodejs", "bun"):
        pkg = read_json(os.path.join(project_dir, "package.json"))
        if pkg:
            engines = pkg.get("engines", {})
            node_ver = engines.get("node")
            if node_ver:
                # Извлечь основную версию: ">=18", "^20", "18.x", "20" → "18" или "20"
                m = re.search(r"(\d+)", node_ver)
                if m:
                    return m.group(1)

        # .nvmrc
        nvmrc = read_file(os.path.join(project_dir, ".nvmrc"))
        if nvmrc:
            m = re.search(r"(\d+)", nvmrc.strip())
            if m:
                return m.group(1)

        # .node-version
        node_ver_file = read_file(os.path.join(project_dir, ".node-version"))
        if node_ver_file:
            m = re.search(r"(\d+)", node_ver_file.strip())
            if m:
                return m.group(1)

    if runtime == "python":
        # .python-version
        py_ver = read_file(os.path.join(project_dir, ".python-version"))
        if py_ver:
            ver = py_ver.strip().split("\n")[0].strip()
            if ver:
                return ver

        # pyproject.toml: requires-python
        pyproject = read_file(os.path.join(project_dir, "pyproject.toml"))
        if pyproject:
            m = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', pyproject)
            if m:
                ver_str = m.group(1)
                ver_m = re.search(r"(\d+\.\d+)", ver_str)
                if ver_m:
                    return ver_m.group(1)

        # runtime.txt (Heroku-style)
        runtime_txt = read_file(os.path.join(project_dir, "runtime.txt"))
        if runtime_txt:
            m = re.search(r"python-(\d+\.\d+)", runtime_txt.strip())
            if m:
                return m.group(1)

    return None


def detect_framework(project_dir, runtime):
    """Определяет фреймворк по зависимостям."""
    if runtime in ("nodejs", "bun"):
        pkg = read_json(os.path.join(project_dir, "package.json"))
        if not pkg:
            return None
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        frameworks = [
            ("next", "Next.js"), ("nuxt", "Nuxt.js"),
            ("@sveltejs/kit", "SvelteKit"), ("@remix-run/react", "Remix"),
            ("astro", "Astro"),
            ("@angular/core", "Angular"),
            ("svelte", "Svelte"), ("vue", "Vue.js"), ("react", "React"),
            ("@nestjs/core", "NestJS"), ("express", "Express"), ("fastify", "Fastify"),
            ("hapi", "Hapi"), ("koa", "Koa"), ("gatsby", "Gatsby"),
        ]
        for dep, name in frameworks:
            if dep in deps:
                return name
        return None

    if runtime == "deno":
        deno_json = read_json(os.path.join(project_dir, "deno.json")) or \
                    read_json(os.path.join(project_dir, "deno.jsonc"))
        if deno_json:
            imports = deno_json.get("imports", {})
            for key in imports:
                if "fresh" in key.lower():
                    return "Fresh"
                if "oak" in key.lower():
                    return "Oak"
        return None

    if runtime == "python":
        req_path = os.path.join(project_dir, "requirements.txt")
        pyproject_path = os.path.join(project_dir, "pyproject.toml")
        deps_text = ""
        if os.path.exists(req_path):
            with open(req_path) as f:
                deps_text = f.read().lower()
        if os.path.exists(pyproject_path):
            with open(pyproject_path) as f:
                deps_text += f.read().lower()
        frameworks = [
            ("django", "Django"), ("fastapi", "FastAPI"), ("flask", "Flask"),
            ("celery", "Celery"), ("tornado", "Tornado"), ("aiohttp", "aiohttp"),
        ]
        for dep, name in frameworks:
            if dep in deps_text:
                return name
        return None

    if runtime == "php":
        composer = read_json(os.path.join(project_dir, "composer.json"))
        if composer:
            deps = composer.get("require", {})
            if "laravel/framework" in deps:
                return "Laravel"
            if "symfony/framework-bundle" in deps:
                return "Symfony"
        return None

    if runtime == "go":
        go_mod = os.path.join(project_dir, "go.mod")
        if os.path.exists(go_mod):
            with open(go_mod) as f:
                content = f.read()
            if "github.com/gin-gonic/gin" in content:
                return "Gin"
            if "github.com/gofiber/fiber" in content:
                return "Fiber"
            if "github.com/labstack/echo" in content:
                return "Echo"
            if "github.com/beego/beego" in content:
                return "Beego"
        return None

    return None


def detect_app_type(project_dir, runtime, framework):
    """frontend / backend / fullstack."""
    has_server = False
    has_frontend = False

    if runtime in ("nodejs", "bun"):
        pkg = read_json(os.path.join(project_dir, "package.json"))
        if pkg:
            deps = pkg.get("dependencies", {})
            server_deps = {"express", "fastify", "koa", "hapi", "@nestjs/core"}
            front_deps = {"react", "vue", "svelte", "@angular/core"}
            has_server = bool(server_deps & set(deps.keys()))
            has_frontend = bool(front_deps & set(deps.keys()))

            # SSR/fullstack фреймворки
            if framework in ("Next.js", "Nuxt.js", "SvelteKit", "Remix", "Astro"):
                return "fullstack"

        # Монорепо
        if os.path.isdir(os.path.join(project_dir, "apps")) or \
           os.path.isdir(os.path.join(project_dir, "packages")):
            return "fullstack"

    if runtime == "deno":
        if framework == "Fresh":
            return "fullstack"
        return "backend"

    if runtime == "python":
        has_server = True  # Python — обычно backend
        # Проверим наличие фронтенда
        for d in ["frontend", "client", "web"]:
            if os.path.isdir(os.path.join(project_dir, d)):
                has_frontend = True

    if has_server and has_frontend:
        return "fullstack"
    if has_server:
        return "backend"
    if has_frontend:
        return "frontend"

    # Если непонятно — по runtime
    if runtime in ("python", "go", "java", "php", "ruby", "elixir", "rust", "deno"):
        return "backend"
    return "frontend"


def _detect_prisma_db(project_dir):
    """Парсит schema.prisma для определения провайдера БД."""
    schema_paths = [
        os.path.join(project_dir, "prisma", "schema.prisma"),
        os.path.join(project_dir, "schema.prisma"),
    ]
    for schema_path in schema_paths:
        content = read_file(schema_path)
        if content:
            m = re.search(r'provider\s*=\s*"(postgresql|mysql|sqlite|mongodb|cockroachdb|sqlserver)"', content)
            if m:
                provider = m.group(1)
                mapping = {
                    "postgresql": "postgresql",
                    "mysql": "mysql",
                    "sqlite": "sqlite",
                    "mongodb": "mongodb",
                    "cockroachdb": "postgresql",
                    "sqlserver": "mssql",
                }
                return mapping.get(provider, provider)
    return None


def detect_databases(project_dir):
    """Ищет зависимости БД."""
    dbs = set()
    db_markers = {
        "pg": "postgresql", "postgres": "postgresql",
        "mysql2": "mysql", "mysql": "mysql",
        "mongoose": "mongodb", "mongodb": "mongodb", "pymongo": "mongodb",
        "redis": "redis", "ioredis": "redis",
        "sqlite3": "sqlite", "better-sqlite3": "sqlite", "sqlite": "sqlite",
        "typeorm": None, "sqlalchemy": None, "sequelize": None,
    }

    # Prisma — парсим schema.prisma вместо хардкода
    prisma_db = _detect_prisma_db(project_dir)

    # package.json
    pkg = read_json(os.path.join(project_dir, "package.json"))
    if pkg:
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        # Если есть prisma — используем результат парсинга schema
        if "prisma" in deps or "@prisma/client" in deps:
            if prisma_db:
                dbs.add(prisma_db)

        for dep, db in db_markers.items():
            if dep in deps and db:
                dbs.add(db)

    # requirements.txt
    req_path = os.path.join(project_dir, "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path) as f:
            content = f.read().lower()
        for marker, db in db_markers.items():
            if marker in content and db:
                dbs.add(db)

    # Проверить .env на DATABASE_URL
    env_path = os.path.join(project_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if "DATABASE_URL" in line or "DB_" in line:
                    val = line.split("=", 1)[-1].strip().lower()
                    if "postgres" in val:
                        dbs.add("postgresql")
                    elif "mysql" in val:
                        dbs.add("mysql")
                    elif "mongodb" in val or "mongo" in val:
                        dbs.add("mongodb")
                    elif "redis" in val:
                        dbs.add("redis")
                    elif "sqlite" in val:
                        dbs.add("sqlite")

    return sorted(dbs)


def detect_port(project_dir):
    """Ищет порт в коде, Dockerfile, .env."""
    # Dockerfile EXPOSE
    for df in ["Dockerfile", "dockerfile"]:
        df_path = os.path.join(project_dir, df)
        if os.path.exists(df_path):
            with open(df_path) as f:
                for line in f:
                    m = re.match(r"EXPOSE\s+(\d+)", line)
                    if m:
                        return int(m.group(1))

    # .env PORT=
    for env_file in [".env", ".env.production", ".env.local"]:
        env_path = os.path.join(project_dir, env_file)
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    m = re.match(r"PORT\s*=\s*(\d+)", line.strip())
                    if m:
                        return int(m.group(1))

    # package.json scripts
    pkg = read_json(os.path.join(project_dir, "package.json"))
    if pkg:
        scripts = pkg.get("scripts", {})
        for s in scripts.values():
            m = re.search(r"--port[= ](\d+)", str(s))
            if m:
                return int(m.group(1))

    # Defaults by framework/runtime
    return None


def detect_build_output_dir(project_dir, runtime, framework):
    """Определяет директорию для результатов сборки (dist, build, .next и т.д.)."""
    if runtime not in ("nodejs", "bun"):
        return None

    # Vite config: outDir
    for config_file in ["vite.config.ts", "vite.config.js", "vite.config.mts", "vite.config.mjs"]:
        content = read_file(os.path.join(project_dir, config_file))
        if content:
            m = re.search(r"outDir\s*:\s*['\"]([^'\"]+)['\"]", content)
            if m:
                return m.group(1)
            # Vite по умолчанию — dist
            return "dist"

    # Next.js: output: 'export' → out, иначе .next
    if framework == "Next.js":
        next_config = read_file(os.path.join(project_dir, "next.config.js")) or \
                      read_file(os.path.join(project_dir, "next.config.mjs")) or \
                      read_file(os.path.join(project_dir, "next.config.ts"))
        if next_config and "output" in next_config and "'export'" in next_config:
            return "out"
        return ".next"

    # CRA: react-scripts → build
    pkg = read_json(os.path.join(project_dir, "package.json"))
    if pkg:
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        scripts = pkg.get("scripts", {})
        if "react-scripts" in deps or any("react-scripts" in str(v) for v in scripts.values()):
            return "build"

    # Angular → dist/<project-name> (упрощаем до dist)
    if framework == "Angular":
        return "dist"

    # Gatsby → public
    if framework == "Gatsby":
        return "public"

    # Astro → dist
    if framework == "Astro":
        return "dist"

    # SvelteKit → build
    if framework == "SvelteKit":
        return "build"

    # Remix → build
    if framework == "Remix":
        return "build"

    # По умолчанию — dist (Vite default)
    return "dist"


def detect_env_vars(project_dir):
    """Ищет .env файлы, извлекает переменные."""
    result = {"files": {}, "defined": [], "missing": []}

    env_files = [".env", ".env.local", ".env.production", ".env.example", ".env.sample"]
    for ef in env_files:
        path = os.path.join(project_dir, ef)
        if os.path.exists(path):
            vars_in_file = {}
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        vars_in_file[key] = val
            result["files"][ef] = vars_in_file

    # Определить defined и missing
    main_env = result["files"].get(".env", {})
    example_env = result["files"].get(".env.example", result["files"].get(".env.sample", {}))

    for key, val in main_env.items():
        if val and val not in ("", "YOUR_KEY_HERE", "xxx", "changeme", "TODO"):
            result["defined"].append(key)
        else:
            result["missing"].append(key)

    for key in example_env:
        if key not in main_env:
            result["missing"].append(key)

    return result


def detect_docker(project_dir):
    """Проверяет наличие Docker-файлов."""
    has_dockerfile = os.path.exists(os.path.join(project_dir, "Dockerfile"))
    has_compose = any(
        os.path.exists(os.path.join(project_dir, f))
        for f in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
    )
    has_dockerignore = os.path.exists(os.path.join(project_dir, ".dockerignore"))
    return {"dockerfile": has_dockerfile, "compose": has_compose, "dockerignore": has_dockerignore}


def detect_git(project_dir):
    """Проверяет состояние Git."""
    result = {"initialized": False, "remote": None, "branch": None, "hosting": None, "dirty": False}

    try:
        r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, cwd=project_dir)
        if r.returncode != 0:
            return result
        result["initialized"] = True

        r = subprocess.run(["git", "remote", "get-url", "origin"],
                           capture_output=True, text=True, cwd=project_dir)
        if r.returncode == 0:
            remote = r.stdout.strip()
            result["remote"] = remote
            if "github.com" in remote:
                result["hosting"] = "github"
            elif "gitlab" in remote:
                result["hosting"] = "gitlab"
            elif "bitbucket" in remote:
                result["hosting"] = "bitbucket"

        r = subprocess.run(["git", "branch", "--show-current"],
                           capture_output=True, text=True, cwd=project_dir)
        if r.returncode == 0:
            result["branch"] = r.stdout.strip()

        r = subprocess.run(["git", "status", "--porcelain"],
                           capture_output=True, text=True, cwd=project_dir)
        if r.returncode == 0:
            result["dirty"] = bool(r.stdout.strip())

    except FileNotFoundError:
        pass

    return result


def detect_commands(project_dir, runtime, package_manager):
    """Определяет команды сборки/запуска."""
    result = {"build": None, "start": None, "install": None}

    # Команда установки зависимостей
    install_cmds = {
        "npm": "npm ci",
        "yarn": "yarn install --frozen-lockfile",
        "pnpm": "pnpm install --frozen-lockfile",
        "bun": "bun install --frozen-lockfile",
    }
    if package_manager:
        result["install"] = install_cmds.get(package_manager, "npm ci")

    run_prefix = {
        "npm": "npm run",
        "yarn": "yarn",
        "pnpm": "pnpm",
        "bun": "bun run",
    }
    prefix = run_prefix.get(package_manager, "npm run")

    if runtime in ("nodejs", "bun"):
        pkg = read_json(os.path.join(project_dir, "package.json"))
        if pkg:
            scripts = pkg.get("scripts", {})
            if "build" in scripts:
                result["build"] = f"{prefix} build"
            if "start" in scripts:
                start_prefix = {"npm": "npm", "yarn": "yarn", "pnpm": "pnpm", "bun": "bun"}
                result["start"] = f"{start_prefix.get(package_manager, 'npm')} start"

    if runtime == "python":
        if os.path.exists(os.path.join(project_dir, "manage.py")):
            result["start"] = "python manage.py runserver 0.0.0.0:8000"
        elif os.path.exists(os.path.join(project_dir, "main.py")):
            result["start"] = "uvicorn main:app --host 0.0.0.0 --port 8000"

    if runtime == "go":
        result["build"] = "go build -o app ."
        result["start"] = "./app"

    if runtime == "php":
        if os.path.exists(os.path.join(project_dir, "artisan")):
            result["start"] = "php artisan serve --host=0.0.0.0 --port=8000"
        result["install"] = "composer install --no-dev --optimize-autoloader"

    return result


def detect_monorepo(project_dir):
    """Проверяет, является ли проект монорепо."""
    pkg = read_json(os.path.join(project_dir, "package.json"))
    if pkg and "workspaces" in pkg:
        return True
    for d in ["apps", "packages"]:
        if os.path.isdir(os.path.join(project_dir, d)):
            return True
    for f in ["turbo.json", "nx.json", "lerna.json", "pnpm-workspace.yaml"]:
        if os.path.exists(os.path.join(project_dir, f)):
            return True
    return False


def analyze(project_dir):
    project_dir = os.path.abspath(project_dir)
    if not os.path.isdir(project_dir):
        print(json.dumps({"error": f"Directory not found: {project_dir}"}))
        sys.exit(1)

    runtime = detect_runtime(project_dir)
    framework = detect_framework(project_dir, runtime)
    app_type = detect_app_type(project_dir, runtime, framework)
    port = detect_port(project_dir)
    package_manager = detect_package_manager(project_dir)
    runtime_version = detect_runtime_version(project_dir, runtime)
    build_output_dir = detect_build_output_dir(project_dir, runtime, framework)

    # Дефолтные порты
    if not port:
        defaults = {
            "nodejs": 3000, "bun": 3000, "deno": 8000,
            "python": 8000, "go": 8080, "php": 8080,
            "ruby": 3000, "java": 8080,
        }
        port = defaults.get(runtime)

    result = {
        "runtime": runtime,
        "runtime_version": runtime_version,
        "framework": framework,
        "app_type": app_type,
        "port": port,
        "package_manager": package_manager,
        "build_output_dir": build_output_dir,
        "databases": detect_databases(project_dir),
        "docker": detect_docker(project_dir),
        "env": detect_env_vars(project_dir),
        "git": detect_git(project_dir),
        "commands": detect_commands(project_dir, runtime, package_manager),
        "monorepo": detect_monorepo(project_dir),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Analyze project for deployment")
    parser.add_argument("path", nargs="?", default=".", help="Project directory")
    args = parser.parse_args()
    analyze(args.path)


if __name__ == "__main__":
    main()
