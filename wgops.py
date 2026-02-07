import base64
import os
import subprocess
from pathlib import Path
from typing import Optional

from config import (
    CLIENTS_DIR,
    QR_DIR,
    SERVER_PUBLIC_KEY_PATH,
    WG_DNS,
    WG_ENDPOINT,
    WG_FAKE_KEYS,
    WG_INTERFACE,
    WG_KEYS_DIR,
    WG_LIVE_APPLY,
    WG_RESTART,
    WG_SAVE_KEYS,
)

import qrcode


def run_cmd(cmd: list[str], input_text: Optional[str] = None) -> str:
    result = subprocess.run(
        cmd,
        input=(input_text.encode() if input_text else None),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode().strip() or "Command failed")
    return result.stdout.decode().strip()


def generate_keypair() -> tuple[str, str]:
    if WG_FAKE_KEYS:
        private_key = base64.b64encode(os.urandom(32)).decode()
        public_key = base64.b64encode(os.urandom(32)).decode()
        return private_key, public_key
    private_key = run_cmd(["wg", "genkey"])
    public_key = run_cmd(["wg", "pubkey"], input_text=private_key)
    return private_key, public_key


def load_server_public_key() -> str:
    if SERVER_PUBLIC_KEY_PATH.exists():
        return SERVER_PUBLIC_KEY_PATH.read_text().strip()
    raise RuntimeError(f"Server public key not found: {SERVER_PUBLIC_KEY_PATH}")


def maybe_save_keys(name: str, private_key: str, public_key: str) -> None:
    if not WG_SAVE_KEYS:
        return
    WG_KEYS_DIR.mkdir(parents=True, exist_ok=True)
    (WG_KEYS_DIR / f"{name}_private").write_text(private_key)
    (WG_KEYS_DIR / f"{name}_public").write_text(public_key)


def build_client_config(private_key: str, client_ip: str) -> str:
    server_public = load_server_public_key()
    return "\n".join(
        [
            "[Interface]",
            f"PrivateKey = {private_key}",
            f"Address = {client_ip}/32",
            f"DNS = {WG_DNS}",
            "",
            "[Peer]",
            f"PublicKey = {server_public}",
            f"Endpoint = {WG_ENDPOINT}",
            "AllowedIPs = 0.0.0.0/0",
            "PersistentKeepalive = 20",
            "",
        ]
    )


def save_config_file(name: str, config_text: str) -> Path:
    CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CLIENTS_DIR / f"{name}.conf"
    path.write_text(config_text)
    return path


def save_qr_png(name: str, config_text: str) -> Path:
    QR_DIR.mkdir(parents=True, exist_ok=True)
    path = QR_DIR / f"{name}.png"
    img = qrcode.make(config_text)
    img.save(path)
    return path


def restart_wireguard() -> None:
    if not WG_RESTART:
        return
    run_cmd(["systemctl", "restart", f"wg-quick@{WG_INTERFACE}"])


def apply_live_add_peer(public_key: str, ip: str) -> None:
    if not WG_LIVE_APPLY or WG_FAKE_KEYS:
        return
    run_cmd(
        ["wg", "set", WG_INTERFACE, "peer", public_key, "allowed-ips", f"{ip}/32"]
    )


def apply_live_remove_peer(public_key: str) -> None:
    if not WG_LIVE_APPLY or WG_FAKE_KEYS:
        return
    run_cmd(["wg", "set", WG_INTERFACE, "peer", public_key, "remove"])
