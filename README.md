# VPNApp — WireGuard User Manager

Небольшой веб‑сервис для управления WireGuard пользователями: добавление/удаление пиров, авто‑выбор свободного IP, генерация конфигов и QR.

## Что умеет

- Веб‑страница с формой и списком пиров
- SQLite база `data/peers.db`
- Импорт существующих пиров из `wg0.conf` (имена берутся из комментариев)
- Автоматическая генерация ключей, `.conf` и QR (PNG)
- Добавление/удаление пиров в `wg0.conf`
- Экспорт конфига и QR

## Быстрый старт (локально, безопасно)

Создай `.env` в корне проекта:

```env
WG_CONF_PATH=./wg0.conf
SERVER_PUBLIC_KEY_PATH=./server_public.key
WG_ENDPOINT=127.0.0.1:51830
WG_DNS=8.8.8.8
WG_NETWORK=10.0.0.0/24
WG_RESTART=0
WG_FAKE_KEYS=1
IMPORT_ON_START=1
```

Положи любой ключ в `server_public.key`, например `fake_server_key`.

Запуск:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Продакшен (на сервере)

Пример `.env`:

```env
WG_CONF_PATH=/etc/wireguard/wg0.conf
SERVER_PUBLIC_KEY_PATH=/etc/wireguard/keys/publickey
WG_ENDPOINT=94.103.95.96:51830
WG_DNS=8.8.8.8
WG_NETWORK=10.0.0.0/24
WG_INTERFACE=wg0
WG_RESTART=1
WG_FAKE_KEYS=0
WG_SAVE_KEYS=0
IMPORT_ON_START=1
```

Запуск:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Переменные окружения

- `WG_CONF_PATH` — путь к `wg0.conf`
- `SERVER_PUBLIC_KEY_PATH` — публичный ключ сервера
- `WG_ENDPOINT` — endpoint сервера `IP:PORT`
- `WG_DNS` — DNS для клиентов
- `WG_NETWORK` — сеть WireGuard, например `10.0.0.0/24`
- `WG_INTERFACE` — имя интерфейса, по умолчанию `wg0`
- `WG_RESTART` — `1/0`, перезапускать ли `wg-quick@wg0`
- `WG_FAKE_KEYS` — `1/0`, использовать фейковые ключи (для локальных тестов)
- `WG_SAVE_KEYS` — `1/0`, сохранять ли ключи в `WG_KEYS_DIR`
- `WG_KEYS_DIR` — директория ключей, по умолчанию `/etc/wireguard/keys`
- `IMPORT_ON_START` — `1/0`, импорт существующих пиров из `wg0.conf`

## Безопасность

- Сервис должен иметь доступ на запись к `wg0.conf` и возможность рестарта `wg-quick@wg0`.
- В базе хранится приватный ключ клиента.
- Не открывай сервис в интернет без авторизации.

## Заметки по импорту

- Имя пира берется из ближайшего комментария `# name` перед блоком `[Peer]`.
- Если имена конфликтуют — имя дополняется суффиксом `-<last_octet>`.
