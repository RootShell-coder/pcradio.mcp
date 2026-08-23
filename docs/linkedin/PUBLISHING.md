# Publication guide

## Recommended title

**Зачем я добавил MCP к интернет-радио на ESP32**

## Alternative titles

- **MCP для ESP32: полезный интерфейс или учебный эксперимент?**
- **Как я подключал нейросеть к PCRadio и где она оказалась лишней**

## LinkedIn preview

PCRadio уже умело работать самостоятельно: воспроизводить станции, управляться
через веб-интерфейс и принимать команды через HTTP API. MCP не был необходимой
частью радио. Я добавил его как эксперимент, чтобы проверить, насколько надёжно
языковая модель может управлять физическим устройством и где обычный код всё ещё
лучше нейросети.

## Images

1. Use `assets/pcradio-mcp-cover.png` as the cover image.
2. Place `assets/architecture.svg` after the section "Что такое MCP в этом
   проекте". Export it to PNG if the LinkedIn editor does not accept SVG.

### Alt text

- Cover: `Прототип интернет-радио на ESP32-S3, подключённый к аудиомодулю и колонке.`
- Diagram: `Пользователь передаёт запрос языковой модели, модель вызывает MCP-сервер, а сервер управляет PCRadio через HTTP API.`

## Suggested post text

MCP часто воспринимают как обязательный мост между устройством и нейросетью. В
моём случае всё было наоборот: PCRadio уже полностью работало, а MCP стал
учебным экспериментом. В статье рассказываю, где модель помогла, где начала
ошибаться и почему детерминированные команды лучше оставить обычному коду.

Проект: https://github.com/RootShell-coder/pcradio.esp32

## Hashtags

`#ESP32 #MCP #IoT #Embedded #AI #OpenSource`

## Checklist

- Verify both repository links before publication.
- Upload the cover at its original aspect ratio.
- Check that LinkedIn preserved headings and numbered lists.
- Add both image descriptions as alt text.
- Remove the alternative titles and this guide from the published article.
- Do not claim that MCP is required for PCRadio playback or device operation.
