#!/usr/bin/env python3
"""Обёртка над Timeweb Cloud API. Убирает ручную сборку curl-команд."""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

BASE_URL = "https://api.timeweb.cloud/api/v1"
MAX_WAIT_ATTEMPTS = 5
INITIAL_WAIT_SEC = 60
RETRY_WAIT_SEC = 30

# Retry-конфигурация по HTTP-кодам
RETRY_CODES = {
    429: {"wait": 5, "max_retries": 3, "reason": "rate limit"},
    500: {"wait": 30, "max_retries": 3, "reason": "internal error"},
    423: {"wait": 10, "max_retries": 3, "reason": "resource locked"},
}


def get_token():
    token = os.environ.get("TIMEWEB_CLOUD_TOKEN")
    if not token:
        env_path = os.path.expanduser("~/.config/timeweb/.env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("TIMEWEB_CLOUD_TOKEN="):
                        token = line.strip().split("=", 1)[1]
    if not token:
        print("ERROR: TIMEWEB_CLOUD_TOKEN not found. Set env var or save to ~/.config/timeweb/.env", file=sys.stderr)
        sys.exit(1)
    return token


def api_request(method, endpoint, data=None, token=None):
    token = token or get_token()
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = json.dumps(data).encode() if data else None

    last_error = None
    for attempt in range(4):  # 1 initial + 3 retries max
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=SSL_CONTEXT) as resp:
                resp_body = resp.read().decode()
                return json.loads(resp_body) if resp_body.strip() else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            last_error = {"error": True, "status": e.code, "message": error_body}

            retry_config = RETRY_CODES.get(e.code)
            if retry_config and attempt < retry_config["max_retries"]:
                wait = retry_config["wait"]
                reason = retry_config["reason"]
                print(f"HTTP {e.code} ({reason}), retry {attempt + 1}/{retry_config['max_retries']} in {wait}s...",
                      file=sys.stderr)
                time.sleep(wait)
                continue

            # Не retryable или исчерпаны попытки
            print(json.dumps(last_error))
            sys.exit(1)

    # Если все retry исчерпаны
    print(json.dumps(last_error))
    sys.exit(1)


def check_token():
    result = api_request("GET", "/account/status")
    print(json.dumps({"ok": True, "status": result}))


def get_balance():
    result = api_request("GET", "/account/finances")
    balance = result.get("finances", {}).get("balance", 0)
    print(json.dumps({"ok": True, "balance": balance}))


def get_server_presets():
    result = api_request("GET", "/presets/servers")
    print(json.dumps(result))


def get_os_images():
    result = api_request("GET", "/os/servers")
    print(json.dumps(result))


def get_app_frameworks():
    result = api_request("GET", "/apps/frameworks")
    print(json.dumps(result))


def get_app_presets():
    result = api_request("GET", "/apps/presets")
    print(json.dumps(result))


def get_db_presets():
    result = api_request("GET", "/presets/dbs")
    print(json.dumps(result))


def list_servers():
    """Список всех серверов с основной информацией."""
    result = api_request("GET", "/servers")
    servers = result.get("servers", [])
    summary = []
    for s in servers:
        ipv4 = None
        for net in s.get("networks", []):
            if net.get("type") == "public":
                for ip in net.get("ips", []):
                    if ip.get("type") == "ipv4":
                        ipv4 = ip.get("ip")
        summary.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "status": s.get("status"),
            "ipv4": ipv4,
            "os": s.get("os", {}).get("name"),
        })
    print(json.dumps({"ok": True, "servers": summary}, ensure_ascii=False))


def list_apps():
    """Список всех приложений App Platform."""
    result = api_request("GET", "/apps")
    apps = result.get("apps", [])
    summary = []
    for a in apps:
        domains = [d.get("fqdn") for d in a.get("domains", []) if d.get("fqdn")]
        summary.append({
            "id": a.get("id"),
            "name": a.get("name"),
            "status": a.get("status"),
            "type": a.get("type"),
            "domains": domains,
            "is_auto_deploy": a.get("repository", {}).get("is_auto_deploy"),
        })
    print(json.dumps({"ok": True, "apps": summary}, ensure_ascii=False))


def list_dbs():
    """Список всех баз данных."""
    result = api_request("GET", "/dbs")
    dbs = result.get("dbs", [])
    summary = []
    for d in dbs:
        summary.append({
            "id": d.get("id"),
            "name": d.get("name"),
            "type": d.get("type"),
            "status": d.get("status"),
            "host": d.get("host"),
            "port": d.get("port"),
        })
    print(json.dumps({"ok": True, "dbs": summary}, ensure_ascii=False))


def upload_ssh_key(name, pub_key_path):
    with open(os.path.expanduser(pub_key_path)) as f:
        pub_key = f.read().strip()
    result = api_request("POST", "/ssh-keys", {"name": name, "body": pub_key, "is_default": False})
    print(json.dumps(result))


def create_server(name, preset_id, os_id, ssh_key_ids=None):
    data = {
        "name": name,
        "comment": "Deployed by AI agent",
        "os_id": int(os_id),
        "preset_id": int(preset_id),
        "bandwidth": 1000,
        "is_ddos_guard": False,
        "is_local_network": False,
    }
    if ssh_key_ids:
        data["ssh_keys_ids"] = [int(k) for k in ssh_key_ids]
    result = api_request("POST", "/servers", data)
    server = result.get("server", {})
    server_id = server.get("id")
    print(json.dumps({"ok": True, "server_id": server_id, "status": server.get("status")}))
    return server_id


def wait_for_server(server_id):
    """Ждёт готовности сервера. Макс ~3.5 мин (60с + 5*30с)."""
    print(f"Waiting {INITIAL_WAIT_SEC}s for server {server_id}...", file=sys.stderr)
    time.sleep(INITIAL_WAIT_SEC)

    for attempt in range(1, MAX_WAIT_ATTEMPTS + 1):
        result = api_request("GET", f"/servers/{server_id}")
        server = result.get("server", {})
        status = server.get("status")
        if status == "on":
            # Извлечь IPv4
            ipv4 = None
            for net in server.get("networks", []):
                if net.get("type") == "public":
                    for ip in net.get("ips", []):
                        if ip.get("type") == "ipv4":
                            ipv4 = ip.get("ip")
            if not ipv4:
                # Запросить IPv4
                print("No IPv4 found, requesting...", file=sys.stderr)
                ip_result = api_request("POST", f"/servers/{server_id}/ips", {"type": "ipv4"})
                ipv4 = ip_result.get("server_ip", {}).get("ip")
                time.sleep(15)
            print(json.dumps({"ok": True, "server_id": server_id, "status": "on", "ipv4": ipv4}))
            return
        print(f"Attempt {attempt}/{MAX_WAIT_ATTEMPTS}: status={status}", file=sys.stderr)
        time.sleep(RETRY_WAIT_SEC)

    print(json.dumps({"ok": False, "error": f"Server not ready after {MAX_WAIT_ATTEMPTS} attempts"}))
    sys.exit(1)


def create_app(name, app_type, preset_id, framework_id, repo_url, branch="main",
               env_vars=None, build_cmd=None, run_cmd=None, auto_deploy=True):
    # App Platform поддерживает только backend и frontend.
    # fullstack деплоится как backend (SSR-фреймворки вроде Next.js/Nuxt.js работают как backend).
    if app_type == "fullstack":
        app_type = "backend"

    data = {
        "name": name,
        "type": app_type,
        "preset_id": int(preset_id),
        "framework_id": int(framework_id),
        "repository": {
            "url": repo_url,
            "branch": branch,
            "is_auto_deploy": auto_deploy,
        },
        "comment": "Deployed by AI agent",
    }
    if env_vars:
        data["env_variables"] = [{"key": k, "value": v} for k, v in env_vars.items()]
    if build_cmd:
        data["build_command"] = build_cmd
    if run_cmd:
        data["run_command"] = run_cmd
    result = api_request("POST", "/apps", data)
    print(json.dumps(result))


def get_app_status(app_id):
    result = api_request("GET", f"/apps/{app_id}")
    print(json.dumps(result))


def get_app_logs(app_id):
    result = api_request("GET", f"/apps/{app_id}/logs")
    print(json.dumps(result))


def create_db(name, db_type, preset_id, login="appuser", password=None):
    if not password:
        import secrets
        password = secrets.token_urlsafe(24)
    data = {
        "name": name,
        "type": db_type,
        "preset_id": int(preset_id),
        "login": login,
        "password": password,
        "hash_type": "caching_sha2",
        "config_parameters": {},
    }
    result = api_request("POST", "/dbs", data)
    db = result.get("db", {})
    print(json.dumps({
        "ok": True,
        "db_id": db.get("id"),
        "host": db.get("host"),
        "port": db.get("port"),
        "login": login,
        "password": password,
        "name": db.get("name"),
    }))


def add_domain(fqdn):
    result = api_request("POST", "/domains", {"fqdn": fqdn})
    print(json.dumps(result))


def add_dns_record(fqdn, subdomain, record_type, value):
    result = api_request("POST", f"/domains/{fqdn}/dns-records", {
        "subdomain": subdomain,
        "type": record_type,
        "value": value,
    })
    print(json.dumps(result))


def check_domain_available(fqdn):
    result = api_request("GET", f"/domains/available?fqdn={fqdn}")
    print(json.dumps(result))


def delete_server(server_id):
    api_request("DELETE", f"/servers/{server_id}")
    print(json.dumps({"ok": True, "deleted": "server", "id": server_id}))


def delete_db(db_id):
    api_request("DELETE", f"/dbs/{db_id}")
    print(json.dumps({"ok": True, "deleted": "db", "id": db_id}))


def delete_app(app_id):
    api_request("DELETE", f"/apps/{app_id}")
    print(json.dumps({"ok": True, "deleted": "app", "id": app_id}))


def main():
    parser = argparse.ArgumentParser(description="Timeweb Cloud API wrapper")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check-token")
    sub.add_parser("balance")
    sub.add_parser("server-presets")
    sub.add_parser("os-images")
    sub.add_parser("app-frameworks")
    sub.add_parser("app-presets")
    sub.add_parser("db-presets")
    sub.add_parser("list-servers")
    sub.add_parser("list-apps")
    sub.add_parser("list-dbs")

    p = sub.add_parser("upload-ssh-key")
    p.add_argument("--name", required=True)
    p.add_argument("--pub-key-path", required=True)

    p = sub.add_parser("create-server")
    p.add_argument("--name", required=True)
    p.add_argument("--preset", required=True, type=int)
    p.add_argument("--os", required=True, type=int)
    p.add_argument("--ssh-keys", nargs="*", type=int)

    p = sub.add_parser("wait-server")
    p.add_argument("--id", required=True, type=int)

    p = sub.add_parser("create-app")
    p.add_argument("--name", required=True)
    p.add_argument("--type", required=True, choices=["backend", "frontend", "fullstack"])
    p.add_argument("--preset", required=True, type=int)
    p.add_argument("--framework", required=True, type=int)
    p.add_argument("--repo-url", required=True)
    p.add_argument("--branch", default="main")
    p.add_argument("--env", nargs="*", help="KEY=VALUE pairs")
    p.add_argument("--build-cmd")
    p.add_argument("--run-cmd")
    p.add_argument("--no-auto-deploy", action="store_true")

    p = sub.add_parser("app-status")
    p.add_argument("--id", required=True, type=int)

    p = sub.add_parser("app-logs")
    p.add_argument("--id", required=True, type=int)

    p = sub.add_parser("create-db")
    p.add_argument("--name", required=True)
    p.add_argument("--type", required=True, choices=["postgres", "mysql", "mongodb", "redis"])
    p.add_argument("--preset", required=True, type=int)
    p.add_argument("--login", default="appuser")
    p.add_argument("--password")

    p = sub.add_parser("add-domain")
    p.add_argument("--fqdn", required=True)

    p = sub.add_parser("add-dns")
    p.add_argument("--fqdn", required=True)
    p.add_argument("--subdomain", required=True)
    p.add_argument("--type", required=True, choices=["A", "AAAA", "CNAME", "MX", "TXT"])
    p.add_argument("--value", required=True)

    p = sub.add_parser("check-domain")
    p.add_argument("--fqdn", required=True)

    p = sub.add_parser("delete-server")
    p.add_argument("--id", required=True, type=int)

    p = sub.add_parser("delete-db")
    p.add_argument("--id", required=True, type=int)

    p = sub.add_parser("delete-app")
    p.add_argument("--id", required=True, type=int)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd = args.command
    if cmd == "check-token":
        check_token()
    elif cmd == "balance":
        get_balance()
    elif cmd == "server-presets":
        get_server_presets()
    elif cmd == "os-images":
        get_os_images()
    elif cmd == "app-frameworks":
        get_app_frameworks()
    elif cmd == "app-presets":
        get_app_presets()
    elif cmd == "db-presets":
        get_db_presets()
    elif cmd == "list-servers":
        list_servers()
    elif cmd == "list-apps":
        list_apps()
    elif cmd == "list-dbs":
        list_dbs()
    elif cmd == "upload-ssh-key":
        upload_ssh_key(args.name, args.pub_key_path)
    elif cmd == "create-server":
        create_server(args.name, args.preset, args.os, args.ssh_keys)
    elif cmd == "wait-server":
        wait_for_server(args.id)
    elif cmd == "create-app":
        env_vars = {}
        if args.env:
            for pair in args.env:
                k, v = pair.split("=", 1)
                env_vars[k] = v
        create_app(args.name, args.type, args.preset, args.framework,
                    args.repo_url, args.branch, env_vars or None,
                    args.build_cmd, args.run_cmd, not args.no_auto_deploy)
    elif cmd == "app-status":
        get_app_status(args.id)
    elif cmd == "app-logs":
        get_app_logs(args.id)
    elif cmd == "create-db":
        create_db(args.name, args.type, args.preset, args.login, args.password)
    elif cmd == "add-domain":
        add_domain(args.fqdn)
    elif cmd == "add-dns":
        add_dns_record(args.fqdn, args.subdomain, args.type, args.value)
    elif cmd == "check-domain":
        check_domain_available(args.fqdn)
    elif cmd == "delete-server":
        delete_server(args.id)
    elif cmd == "delete-db":
        delete_db(args.id)
    elif cmd == "delete-app":
        delete_app(args.id)


if __name__ == "__main__":
    main()
