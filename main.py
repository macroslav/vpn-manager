import re
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import APP_TITLE, IMPORT_ON_START, WG_NETWORK
from db import (
    ensure_dirs,
    find_peer_by_id,
    find_peer_by_name,
    insert_peer,
    list_ips_from_db,
    list_peers,
    delete_peer as db_delete_peer,
    init_db,
    import_peers,
)
from wgconf import (
    append_peer_to_conf,
    list_used_ips_from_conf,
    parse_peers_from_conf,
    remove_peer_from_conf,
)
from wgops import (
    build_client_config,
    generate_keypair,
    maybe_save_keys,
    restart_wireguard,
    save_config_file,
    save_qr_png,
)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=APP_TITLE)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "peer"


def find_free_ip() -> str:
    import ipaddress

    net = ipaddress.ip_network(WG_NETWORK, strict=False)
    used = list_used_ips_from_conf() | list_ips_from_db()
    for host in net.hosts():
        ip = str(host)
        if ip.endswith(".1"):
            continue
        if ip not in used:
            return ip
    raise RuntimeError("No free IPs available in WG_NETWORK")


def create_peer(name: str) -> int:
    name = name.strip()
    if not name:
        raise ValueError("Name is required")

    existing = find_peer_by_name(name)
    if existing:
        raise ValueError("Name already exists")

    private_key, public_key = generate_keypair()
    ip = find_free_ip()
    client_config = build_client_config(private_key, ip)

    safe_name = safe_filename(name)
    config_path = save_config_file(safe_name, client_config)
    qr_path = save_qr_png(safe_name, client_config)
    maybe_save_keys(safe_name, private_key, public_key)

    append_peer_to_conf(name, public_key, ip)
    restart_wireguard()

    return insert_peer(
        name=name,
        ip=ip,
        public_key=public_key,
        private_key=private_key,
        config_path=str(config_path),
        qr_path=str(qr_path),
    )


def delete_peer(peer_id: int) -> None:
    row = find_peer_by_id(peer_id)
    if not row:
        raise ValueError("Peer not found")

    remove_peer_from_conf(row["ip"])
    restart_wireguard()

    for path in [row["config_path"], row["qr_path"]]:
        if not path:
            continue
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass

    db_delete_peer(peer_id)


@app.on_event("startup")
def on_startup() -> None:
    ensure_dirs()
    init_db()
    if IMPORT_ON_START:
        records = parse_peers_from_conf()
        if records:
            import_peers(records)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    rows = list_peers()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "peers": rows, "title": APP_TITLE},
    )


@app.post("/peers")
def create_peer_form(name: str = Form(...)):
    try:
        peer_id = create_peer(name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url=f"/?created={peer_id}", status_code=303)


@app.post("/peers/{peer_id}/delete")
def delete_peer_form(peer_id: int):
    try:
        delete_peer(peer_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url="/?deleted=1", status_code=303)


@app.get("/peers/{peer_id}/config")
def download_config(peer_id: int):
    row = find_peer_by_id(peer_id)
    if not row:
        raise HTTPException(status_code=404, detail="Peer not found")
    if not row["config_path"]:
        raise HTTPException(status_code=404, detail="Config not available for this peer")
    path = Path(row["config_path"])
    return FileResponse(
        path,
        filename=f"{safe_filename(row['name'])}.conf",
        media_type="application/octet-stream",
    )


@app.get("/peers/{peer_id}/qr")
def download_qr(peer_id: int):
    row = find_peer_by_id(peer_id)
    if not row:
        raise HTTPException(status_code=404, detail="Peer not found")
    if not row["qr_path"]:
        raise HTTPException(status_code=404, detail="QR not available for this peer")
    path = Path(row["qr_path"])
    return FileResponse(
        path,
        filename=f"{safe_filename(row['name'])}.png",
        media_type="application/octet-stream",
    )


@app.get("/api/peers")
def api_peers():
    rows = list_peers()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "ip": row["ip"],
            "public_key": row["public_key"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
