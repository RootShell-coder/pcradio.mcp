# pcradio-mcp

MCP-сервер для управления интернет-радио PCRadio через HTTP API. Использует
Streamable HTTP.

## Возможности

- чтение состояния устройства и плейлиста;
- управление воспроизведением, каналом, громкостью и mute;
- настройка EQ и звуковых эффектов;
- управление пользовательскими станциями и будильниками;
- установка NTP-серверов и timezone.

Операции удаления, OTA, standby и IR service не экспортируются.

## Запуск

```bash
git clone https://github.com/RootShell-coder/pcradio.mcp.git
cd pcradio.mcp
export PCRADIO_BASE_URL=http://pcradio.local
docker compose pull
docker compose up -d
```

MCP endpoint:

```text
http://localhost:8081/mcp
```

## Конфигурация

| Переменная         | Назначение                | По умолчанию           |
| ------------------ | ------------------------- | ---------------------- |
| `PCRADIO_BASE_URL` | URL HTTP API устройства   | `http://pcradio.local` |
| `PCRADIO_TIMEOUT`  | Таймаут запросов, секунды | `5`                    |
| `MCP_HOST`         | Адрес внутри контейнера   | `0.0.0.0`              |
| `MCP_PORT`         | Порт внутри контейнера    | `8080`                 |

Значения можно задать через переменные окружения или файл `.env`.

## Проверка

Read-only smoke-тест не выполняет операции записи:

```bash
docker compose run --rm --no-deps \
  -v ./tests:/tests:ro \
  pcradio-mcp python /tests/read_mcp.py
```
