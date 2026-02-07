import re
from pathlib import Path

from config import WG_CONF_PATH


def read_wg_conf() -> list[str]:
    if not WG_CONF_PATH.exists():
        raise RuntimeError(f"wg0.conf not found: {WG_CONF_PATH}")
    return WG_CONF_PATH.read_text().splitlines()


def write_wg_conf(lines: list[str]) -> None:
    content = "\n".join(lines).rstrip() + "\n"
    WG_CONF_PATH.write_text(content)


def list_used_ips_from_conf() -> set[str]:
    lines = read_wg_conf()
    used = set()
    for line in lines:
        line = line.strip()
        if line.lower().startswith("allowedips"):
            _, value = line.split("=", 1)
            ip = value.strip().split("/")[0]
            if ip:
                used.add(ip)
    return used


def append_peer_to_conf(name: str, public_key: str, ip: str) -> None:
    lines = read_wg_conf()
    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.extend(
        [
            f"# {name}",
            "[Peer]",
            f"PublicKey = {public_key}",
            f"AllowedIPs = {ip}/32",
            "",
        ]
    )
    write_wg_conf(lines)


def remove_peer_from_conf(ip: str) -> None:
    lines = read_wg_conf()
    peer_indices = [i for i, line in enumerate(lines) if line.strip() == "[Peer]"]
    if not peer_indices:
        return

    blocks = []
    for idx, start in enumerate(peer_indices):
        end = peer_indices[idx + 1] if idx + 1 < len(peer_indices) else len(lines)
        block_start = start
        while block_start - 1 >= 0 and lines[block_start - 1].strip().startswith("#"):
            block_start -= 1
        blocks.append((block_start, end))

    target_block = None
    for block_start, block_end in blocks:
        block_text = "\n".join(lines[block_start:block_end])
        if f"AllowedIPs = {ip}/32" in block_text:
            target_block = (block_start, block_end)
            break

    if not target_block:
        return

    block_start, block_end = target_block
    new_lines = lines[:block_start] + lines[block_end:]
    write_wg_conf(new_lines)


def parse_peers_from_conf() -> list[dict[str, str]]:
    lines = read_wg_conf()
    peers = []
    current_comments: list[str] = []
    in_peer = False
    public_key = None
    allowed_ip = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            comment = line.lstrip("#").strip()
            if comment:
                current_comments.append(comment)
            continue
        if line == "[Peer]":
            in_peer = True
            public_key = None
            allowed_ip = None
            continue
        if line.startswith("[") and line.endswith("]") and line != "[Peer]":
            in_peer = False
            current_comments = []
            continue
        if in_peer:
            match = re.match(r"PublicKey\s*=\s*(.+)", line, re.IGNORECASE)
            if match:
                public_key = match.group(1).strip()
            match = re.match(r"AllowedIPs\s*=\s*(.+)", line, re.IGNORECASE)
            if match:
                allowed_ip = match.group(1).strip().split("/")[0]

        if in_peer and public_key and allowed_ip:
            name = current_comments[-1] if current_comments else f"peer-{allowed_ip.split('.')[-1]}"
            peers.append({"name": name, "public_key": public_key, "ip": allowed_ip})
            in_peer = False
            current_comments = []
            public_key = None
            allowed_ip = None

    return peers
