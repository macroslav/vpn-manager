import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_TITLE = "WireGuard User Manager"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CLIENTS_DIR = DATA_DIR / "clients"
QR_DIR = DATA_DIR / "qr"
DB_PATH = DATA_DIR / "peers.db"

WG_CONF_PATH = Path(os.getenv("WG_CONF_PATH", "/etc/wireguard/wg0.conf"))
WG_KEYS_DIR = Path(os.getenv("WG_KEYS_DIR", "/etc/wireguard/keys"))
SERVER_PUBLIC_KEY_PATH = Path(
    os.getenv("SERVER_PUBLIC_KEY_PATH", "/etc/wireguard/keys/publickey")
)
WG_ENDPOINT = os.getenv("WG_ENDPOINT", "94.103.95.96:51830")
WG_DNS = os.getenv("WG_DNS", "8.8.8.8")
WG_NETWORK = os.getenv("WG_NETWORK", "10.0.0.0/24")
WG_INTERFACE = os.getenv("WG_INTERFACE", "wg0")

WG_RESTART = os.getenv("WG_RESTART", "1") == "1"
WG_LIVE_APPLY = os.getenv("WG_LIVE_APPLY", "0") == "1"
WG_FAKE_KEYS = os.getenv("WG_FAKE_KEYS", "0") == "1"
WG_SAVE_KEYS = os.getenv("WG_SAVE_KEYS", "0") == "1"
IMPORT_ON_START = os.getenv("IMPORT_ON_START", "1") == "1"
