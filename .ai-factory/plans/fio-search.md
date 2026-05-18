# Plan: Пробив по ФИО

**Feature:** OSINT-поиск по имени/отчеству/фамилии  
**Created:** 2026-05-18  
**Branch:** n/a (no git)

---

## Settings

- **Testing:** Yes — pytest-тесты для `fio_lookup.py`
- **Logging:** Verbose — DEBUG-логи на каждом шаге, ERROR на каждом источнике отдельно
- **Docs:** Yes — обязательный чекпоинт в Task 7

---

## Roadmap Linkage

- **Milestone:** "Пробив по ФИО"
- **Rationale:** Этот план полностью реализует веху поиска по ФИО из ROADMAP.md

---

## Context

Проект — Telegram-бот на aiogram 3 (Python). Модули в `modules/`, хендлеры в `handlers/`.  
Уже реализован `/breach name ...` через LeakCheck + DeHashed, но это generic-команда.  
Эта веха добавляет **выделенную команду `/fio`** с:
- поиском через breach-базы (LeakCheck, DeHashed, IntelX),
- поиском в VK по имени (`users.search`),
- поиском публичных резюме на HH.ru,
- генерацией вариантов никнеймов из ФИО для дальнейшего ручного поиска.

---

## Tasks

### Phase 1 — Источники данных (можно параллельно)

**Task 1 — Добавить поиск по имени в VK API**  
Файл: `modules/vk_lookup.py`

Добавить функцию:
```python
async def vk_user_search(name: str, count: int = 20) -> dict
```
- Вызывает VK API метод `users.search` с параметром `q=name`
- Поля: `first_name, last_name, photo_100, city, country, bdate, followers_count, screen_name, is_closed`
- Возвращает `{"results": [...], "found": N}` или `{"error": "..."}`
- Логирование: `DEBUG` — старт запроса, кол-во результатов; `ERROR` — ошибки API

---

**Task 2 — Создать модуль поиска по HH.ru**  
Файл: `modules/hh_lookup.py` (новый)

```python
async def hh_resume_search(name: str, per_page: int = 10) -> dict
```
- `GET https://api.hh.ru/resumes?text={name}&per_page={per_page}`
- Без API-ключа (открытый endpoint). Нужен `User-Agent: osint-bot/1.0`
- Возвращает: `{"results": [{"title", "area", "age", "gender", "url", "last_activity"}], "found": N}`
- Логирование: `DEBUG` — запрос/ответ; `WARNING` — 0 результатов; `ERROR` — сетевые ошибки

---

### Phase 2 — Агрегатор и утилиты

**Task 3 — Создать агрегатор-модуль FIO**  
Файл: `modules/fio_lookup.py` (новый)

```python
TRANSLIT_TABLE: dict[str, str] = {...}  # Кириллица → латиница

def transliterate_name(text: str) -> str
    # Использует TRANSLIT_TABLE, без внешних зависимостей

def generate_username_variants(first: str, last: str, middle: str = "") -> list[str]
    # Генерирует варианты: ivanov.ivan, ivan.ivanov, ivanov_i, i_ivanov,
    #                      ivanov, ivanov_ivan, ivan_ivanov, ii_ivanov
    # Всё в нижнем регистре, транслит
    
async def fio_search(
    first: str, last: str, middle: str = "",
    leakcheck_key: str = "", dehashed_email: str = "",
    dehashed_key: str = "", intelx_key: str = ""
) -> dict
    # asyncio.gather() всех источников параллельно:
    #   - leakcheck_search(f"{last} {first}", key, "name")
    #   - dehashed_search(f"{last} {first}", email, key, field="name")
    #   - intelx_search(f"{last} {first}", key)
    #   - vk_user_search(f"{first} {last}")
    #   - hh_resume_search(f"{last} {first}")
    # Возвращает {"breach_lc": ..., "breach_dh": ..., "breach_ix": ...,
    #             "vk": ..., "hh": ..., "username_variants": [...]}
    # Логирование: DEBUG старт каждого источника, DEBUG результат,
    #              ERROR каждого источника отдельно (не прерывает остальные)
```

> ⚠️ Зависит от Task 1 (vk_user_search) и Task 2 (hh_resume_search).

---

### Phase 3 — Хендлер и регистрация

**Task 4 — Создать обработчик /fio**  
Файл: `handlers/fio_h.py` (новый)

```
/fio Иванов Иван Иванович   — три части
/fio Иванов Иван             — две части
```

Логика хендлера:
1. Парсинг: `parts = args.split()` → `last=parts[0]`, `first=parts[1]`, `middle=parts[2] if len>=3`
2. Отправить progress-сообщение: "🔍 Ищу ФИО: ..."
3. Вызвать `fio_search(...)` с API-ключами из `config`
4. Форматировать результат блоками через `utils/formatter.py`:
   - 🗄 **Breach DBs** (LeakCheck / DeHashed / IntelX) — таблица записей
   - 👤 **VK** — список профилей с ссылками
   - 💼 **HH.ru** — список резюме с ссылками
   - 🔤 **Username variants** — список для ручной проверки через `/user`
5. Обрезка текста до 4000 символов (Telegram limit)
6. Логирование: `DEBUG` ввод, `DEBUG` завершение каждого источника, `INFO` итог

> ⚠️ Зависит от Task 3 (fio_lookup.py).

---

**Task 5 — Зарегистрировать fio_router в боте**  
Файлы: `handlers/__init__.py`, `bot.py`

- `handlers/__init__.py`: `from .fio_h import router as fio_router` + добавить в `__all__`
- `bot.py`:
  - Импорт `fio_router`
  - `dp.include_routers(..., fio_router)`
  - `BotCommand(command="fio", description="Поиск по ФИО")`
  - В тексте `/start` и `/help`: добавить `/fio <code>Иванов Иван [Отч]</code> — поиск по ФИО`

> ⚠️ Зависит от Task 4.

---

### Phase 4 — Тесты

**Task 6 — Написать тесты для fio_lookup.py**  
Файл: `tests/test_fio_lookup.py` (новый), `tests/__init__.py` (если нет)

Тест-кейсы (pytest):
1. `test_transliterate_name` — "Иванов" → "Ivanov", "Ёжиков" → "Ezhikov"
2. `test_generate_username_variants` — >=4 вариантов, все строки, нет дублей
3. `test_fio_search_aggregation` — `AsyncMock` для всех источников, проверяет ключи результата
4. `test_fio_search_partial_failure` — один источник бросает Exception, остальные результаты есть

> ⚠️ Зависит от Task 3.

---

### Phase 5 — Документация _(обязательный чекпоинт)_

**Task 7 — Обновить документацию бота**  
Файлы: `bot.py` (уже покрыто Task 5), `README.md` (если существует)

- В `/start` / `/help`: строка `/fio Иванов Иван [Иванович]` уже добавлена в Task 5
- Если `README.md` существует: добавить секцию `### /fio — поиск по ФИО` с примером и списком источников
- Если README нет — не создавать

---

## Commit Plan

| Commit | Задачи | Сообщение |
|--------|--------|-----------|
| #1 | Task 1, 2, 3 | `feat: add vk name search, hh.ru module, fio aggregator` |
| #2 | Task 4, 5 | `feat: add /fio command and register router` |
| #3 | Task 6, 7 | `test: add fio_lookup tests; docs: update bot help` |

---

## Источники данных итого

| Источник | Метод | Ключ нужен | Что возвращает |
|----------|-------|-----------|----------------|
| LeakCheck | `leakcheck_search(..., "name")` | `LEAKCHECK_API_KEY` | Записи из утечек по имени |
| DeHashed | `dehashed_search(..., field="name")` | `DEHASHED_*` | Записи из утечек по имени |
| IntelX | `intelx_search(fullname)` | `INTELX_API_KEY` | Пасты, дампы с упоминанием |
| VK API | `users.search?q=name` | `VK_TOKEN` | Список профилей |
| HH.ru | open API `/resumes?text=name` | нет | Публичные резюме |
| Username variants | транслит + паттерны | — | Список ников для `/user` |
