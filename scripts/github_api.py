#!/usr/bin/env python3
"""Обёртка над GitHub API. Шифрование секретов, deploy keys, создание репо."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

GITHUB_API = "https://api.github.com"


def get_pat():
    pat = os.environ.get("GITHUB_PAT")
    if not pat:
        pat_path = os.path.expanduser("~/.config/timeweb/.github_pat")
        if os.path.exists(pat_path):
            with open(pat_path) as f:
                pat = f.read().strip()
    if not pat:
        print("ERROR: GITHUB_PAT not found. Set env var or save to ~/.config/timeweb/.github_pat", file=sys.stderr)
        sys.exit(1)
    return pat


def gh_request(method, endpoint, data=None, pat=None):
    pat = pat or get_pat()
    url = f"{GITHUB_API}{endpoint}"
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github+json",
    }
    if data:
        headers["Content-Type"] = "application/json"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(json.dumps({"error": True, "status": e.code, "message": error_body}))
        sys.exit(1)


def create_repo(name, private=True):
    result = gh_request("POST", "/user/repos", {"name": name, "private": private})
    print(json.dumps({
        "ok": True,
        "full_name": result.get("full_name"),
        "clone_url": result.get("clone_url"),
        "ssh_url": result.get("ssh_url"),
        "private": result.get("private"),
    }))


def check_repo_visibility(owner, repo):
    result = gh_request("GET", f"/repos/{owner}/{repo}")
    is_private = result.get("private", False)
    print(json.dumps({
        "ok": True,
        "full_name": f"{owner}/{repo}",
        "private": is_private,
        "warning": None if is_private else "REPO IS PUBLIC - secrets may be exposed!",
    }))


def add_deploy_key(owner, repo, pub_key_path, title="timeweb-server"):
    with open(os.path.expanduser(pub_key_path)) as f:
        pub_key = f.read().strip()
    result = gh_request("POST", f"/repos/{owner}/{repo}/keys", {
        "title": title,
        "key": pub_key,
        "read_only": True,
    })
    print(json.dumps({"ok": True, "key_id": result.get("id"), "title": title}))


def _encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    """Шифрует секрет с помощью PyNaCl (libsodium sealed box)."""
    try:
        from base64 import b64encode
        from nacl import encoding, public
    except ImportError:
        print("ERROR: PyNaCl not installed. Run: pip install pynacl", file=sys.stderr)
        sys.exit(1)

    pk = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(secret_value.encode("utf-8"))
    return b64encode(sealed).decode("utf-8")


def set_secret(owner, repo, name, value):
    # Получить публичный ключ репозитория
    pk_data = gh_request("GET", f"/repos/{owner}/{repo}/actions/secrets/public-key")
    repo_pub_key = pk_data["key"]
    key_id = pk_data["key_id"]

    encrypted = _encrypt_secret(repo_pub_key, value)
    gh_request("PUT", f"/repos/{owner}/{repo}/actions/secrets/{name}", {
        "encrypted_value": encrypted,
        "key_id": key_id,
    })
    print(json.dumps({"ok": True, "secret": name, "repo": f"{owner}/{repo}"}))


def set_all_secrets(owner, repo, secrets_json=None, secrets_file=None):
    """Пакетное добавление секретов. Принимает JSON из файла (--secrets-file) или строки."""
    if secrets_file:
        with open(os.path.expanduser(secrets_file)) as f:
            secrets = json.load(f)
    elif secrets_json:
        secrets = json.loads(secrets_json)
    else:
        # Читаем из stdin
        secrets = json.load(sys.stdin)

    # Получить публичный ключ один раз
    pk_data = gh_request("GET", f"/repos/{owner}/{repo}/actions/secrets/public-key")
    repo_pub_key = pk_data["key"]
    key_id = pk_data["key_id"]

    results = []
    for name, value in secrets.items():
        encrypted = _encrypt_secret(repo_pub_key, value)
        gh_request("PUT", f"/repos/{owner}/{repo}/actions/secrets/{name}", {
            "encrypted_value": encrypted,
            "key_id": key_id,
        })
        results.append(name)

    print(json.dumps({"ok": True, "secrets_added": results, "repo": f"{owner}/{repo}"}))


def main():
    parser = argparse.ArgumentParser(description="GitHub API wrapper")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("create-repo")
    p.add_argument("--name", required=True)
    p.add_argument("--public", action="store_true", help="DANGEROUS: create public repo")

    p = sub.add_parser("check-visibility")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)

    p = sub.add_parser("add-deploy-key")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--pub-key-path", required=True)
    p.add_argument("--title", default="timeweb-server")

    p = sub.add_parser("set-secret")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--value", required=True)

    p = sub.add_parser("set-all-secrets")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--secrets", help='JSON string (NOT recommended for sensitive data)')
    p.add_argument("--secrets-file", help='Path to JSON file with secrets (recommended)')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd = args.command
    if cmd == "create-repo":
        create_repo(args.name, private=not args.public)
    elif cmd == "check-visibility":
        check_repo_visibility(args.owner, args.repo)
    elif cmd == "add-deploy-key":
        add_deploy_key(args.owner, args.repo, args.pub_key_path, args.title)
    elif cmd == "set-secret":
        set_secret(args.owner, args.repo, args.name, args.value)
    elif cmd == "set-all-secrets":
        set_all_secrets(args.owner, args.repo, args.secrets, getattr(args, 'secrets_file', None))


if __name__ == "__main__":
    main()
