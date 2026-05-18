# Project Roadmap

> OSINT Telegram-бот для глубокой разведки по открытым источникам: ФИО, телефон, транспорт, соцсети, документы, юрлица, адреса, онлайн-следы и фотографии.

## Milestones (в работе / запланировано)

- [ ] **Глубокий пробив по телефону** — WhatsApp-регистрация, Telegram по номеру, caller-ID базы
- [ ] **Сетевая разведка (Shodan)** — расширенный анализ IP/доменов через Shodan API
- [ ] **Holehe + Maigret — стабильный деплой** — убедиться что оба работают в production

## Ссылки для исследования и имплементации

> Статус: 🔴 не начато | 🟡 исследовано | 🟢 интегрировано

---

### 🔴 Osintgram — Instagram OSINT
**Ссылка:** https://github.com/Datalux/Osintgram
**Что даёт:** Подписчики/подписки, геолокации фото, хештеги, медиа, контакты Instagram-профиля.
**Интеграция:** Python, без встроенного API — вызов через subprocess или прямой импорт кода.
**Команда бота:** `/instagram @username` — расширенный OSINT по Instagram.
**Ограничение:** Только публичные профили или аккаунты подписчиков авторизованного юзера.

---

### 🔴 Photon — веб-краулер
**Ссылка:** https://github.com/s0md3v/Photon
**Что даёт:** Из любого URL извлекает email, поддомены, URL, S3-бакеты, API-ключи, JS-файлы, хэши.
**Интеграция:** `pip install photon` — есть Python API + JSON-вывод. Самый простой для интеграции.
**Команда бота:** `/crawl https://example.com` — глубокий анализ сайта.

---

### 🔴 theHarvester — email/subdomain harvesting
**Ссылка:** https://github.com/laramies/theHarvester
**Что даёт:** Email, поддомены, IP через 60+ источников (Google, Shodan, Censys, CT-логи).
**Интеграция:** Встроенный REST API — вызывать HTTP-запросами из бота. `pip install theHarvester`.
**Команда бота:** Добавить в `/domain` для расширенного поиска email на домене.

---

### 🔴 TorBot — Tor dark web crawler
**Ссылка:** https://github.com/DedSecInside/TorBot
**Что даёт:** Сканирует .onion сайты: заголовки, описания, граф связей, JSON-вывод.
**Интеграция:** subprocess + запущенный Tor-демон в контейнере.
**Команда бота:** `/tor http://site.onion` — анализ onion-ресурса.
**Ограничение:** Требует Tor daemon в k8s pod'е.

---

### 🔴 WhatsApp регистрация по номеру (бесплатно)
**Источник:** devanok / собственный
**Что даёт:** `GET https://api.whatsapp.com/send?phone=79001234567` — HTTP 200 = зарегистрирован.
**Интеграция:** 5 минут, уже почти есть в боте. Добавить в `/phone`.
**Приоритет:** Высокий — быстро и без ключа.

---

### 🔴 htmlweb.ru — бесплатный пробив телефона
**Источник:** devanok (https://htmlweb.ru/geo/api.php?json&telcod=PHONE)
**Что даёт:** Страна, оператор, регион, часовой пояс — бесплатно, без ключа.
**Интеграция:** Простой GET-запрос. Добавить в `/phone` как дополнительный источник.

---

### 🔴 phonebook.space — имена по номерам телефонов
**Источник:** devanok (https://phonebook.space/?number=+PHONE)
**Что даёт:** Имена из телефонных книг по номеру. Скрейпинг HTML.
**Интеграция:** httpx + BeautifulSoup, добавить в `/phone`.

---

### 🔴 search4faces.com — поиск по фото в VK/OK/TikTok
**Источник:** cipher387/osint_stuff_tool_collection
**Что даёт:** Поиск человека по фото в ВКонтакте, Одноклассниках, TikTok, Clubhouse.
**Интеграция:** Через их API или веб-скрейпинг. Добавить в `/image`.
**Приоритет:** Высокий — уникальный источник для российской аудитории.

---

### 🔴 vk.city4me.com — мониторинг онлайна ВКонтакте
**Источник:** cipher387/osint_stuff_tool_collection
**Что даёт:** Отслеживание времени онлайн VK-пользователя.
**Интеграция:** Скрейпинг или API. Добавить в `/vk`.

---

### 🔴 tgstat.com — статистика Telegram каналов
**Источник:** cipher387
**Что даёт:** История роста аудитории, вовлечённость, упоминания канала в других каналах.
**Интеграция:** Их API (платный) или скрейпинг публичных данных. Добавить в `/tg`.

---

### 🔴 analyzeid.com — поиск сайтов по владельцу
**Источник:** cipher387
**Что даёт:** По домену находит другие сайты того же владельца через email, Facebook App ID, nameserver.
**Интеграция:** Скрейпинг или API. Добавить в `/domain`.

---

### 🔴 GeoWiFi — геолокация по WiFi BSSID/SSID
**Источник:** cipher387 / https://github.com/GONZOsint/geowifi
**Что даёт:** Координаты точки доступа по MAC-адресу через Wigle, Apple, OpenWifi.
**Интеграция:** `pip install geowifi` или прямые запросы к Wigle API.
**Команда бота:** `/wifi BSSID` или добавить в IP/сетевой анализ.

---

### 🔴 Cipher387 OSINT коллекция — для дальнейшего изучения
**Ссылка:** https://github.com/cipher387/osint_stuff_tool_collection
**Что это:** 700+ онлайн-инструментов для OSINT, включая Telegram, VK, телефоны, email, транспорт, геолокацию.
**Действие:** Периодически просматривать для новых бесплатных источников.

---

### 🔴 WhatsMyName — 1500+ сайтов для username
**Источник:** lockfale/OSINT-Framework
**Что даёт:** База из 1500+ сайтов с проверкой username. Крупнее Sherlock (400) и наш основа Maigret использует её частично.
**Интеграция:** `https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json` — скачать и использовать как дополнение к Sherlock в нашем username_lookup.
**Приоритет:** Высокий — бесплатно, просто, больше покрытие.

---

### 🔴 breach.vip — 1000+ баз утечек
**Источник:** lockfale/OSINT-Framework
**Что даёт:** Поиск по 1000+ базам утечек, бесплатно.
**Интеграция:** Нужно проверить наличие публичного API.
**Действие:** Исследовать endpoint при имплементации.

---

### 🔴 GHunt — Google-аккаунт OSINT
**Источник:** lockfale/OSINT-Framework
**Что даёт:** По Gmail-адресу находит: имя, фото, YouTube-канал, Google Maps активность, подключённые сервисы.
**Интеграция:** Python, `pip install ghunt`. Требует OAuth-токен Google-аккаунта для авторизации.
**Команда бота:** Добавить в `/email` для Gmail-адресов.

---

### 🔴 SNScrape — парсинг соцсетей без API
**Источник:** cipher387
**Что даёт:** Python-библиотека для парсинга Twitter/X, Instagram, TikTok, Reddit, VK без API-ключей.
**Интеграция:** `pip install snscrape`, импорт как модуль.
**Команда бота:** Поиск постов/профилей по username в соцсетях.

---

### 🔴 Wayback Machine API — архив интернета
**Источник:** cipher387
**Что даёт:** История сайта, удалённые страницы, старые версии. Бесплатно, без ключа.
**Интеграция:** `GET https://archive.org/wayback/available?url=example.com` — 5 минут работы.
**Команда бота:** Добавить в `/domain` как "История сайта".

---

### 🔴 ViewDNS.info API — DNS разведка
**Источник:** lockfale/OSINT-Framework
**Что даёт:** IP History, Reverse IP (все домены на IP), DNS records, Port scan, Whois. Бесплатный tier.
**Интеграция:** `https://api.viewdns.info/...?apikey=KEY` — добавить в `/domain` и `/ip`.

---

### 📋 Коллекции (справочники, не для имплементации)
- https://github.com/jivoi/awesome-osint — 26k★, огромный список OSINT ресурсов
- https://github.com/lockfale/OSINT-Framework — 11k★, интерактивный фреймворк-дерево
- https://github.com/sinwindie/OSINT — методики и инструменты сбора данных

---

### ❌ Нерелевантные репозитории
- `ChenYilong/iOSInterviewQuestions` — вопросы для iOS-разработчиков, не OSINT
- `JeaSungLEE/iOSInterviewquestions` — то же самое
- `Artss1/Falpe_X` — закрытый инструмент с паролем, нет кода для изучения
- `glaz-boga-telegram/sherlock-telegram` — рекламный бот без исходников
- `TheHackMe/PentestOsint` — только гайд/документация, нет кода
- `zakita88/OSINT-Scout-v3` — учебный проект (курсач), нет README
- `lonneecybs-sudo/Geoint-Osint-Telegram-bot` — HTML-документ со списком API ключей
- `piligrimm735/pepeOSINTbot` — пустой репо без кода
- `simonhacer2024termux/AKADA` — только инструкция установки Termux, кода нет

---

## Completed

| Milestone | Date |
|-----------|------|
| Базовая инфраструктура бота | 2026-05-18 |
| Domain & IP OSINT | 2026-05-18 |
| Email + базы утечек | 2026-05-18 |
| Анализ номера телефона | 2026-05-18 |
| Поиск username | 2026-05-18 |
| Соцсети: VK и Telegram | 2026-05-18 |
| Реверс-поиск по фото | 2026-05-18 |
| Пробив по ФИО | 2026-05-18 |
| Поиск по транспорту | 2026-05-18 |
| Документы физлиц | 2026-05-18 |
| Юридические лица (ЮЛ/ИП) | 2026-05-18 |
| Расширенные соцсети | 2026-05-18 |
| Адреса и недвижимость | 2026-05-18 |
| Сводный OSINT-отчёт | 2026-05-18 |
| Распознавание лиц | 2026-05-18 |
| Sherlock (414 сайтов) в username-поиске | 2026-05-18 |
| Maigret (3000+ сайтов) параллельный поиск | 2026-05-18 |
| Holehe (144 сервиса) email-регистрации | 2026-05-18 |
| Scylla/Cassandra/SFS/Tor-check без ключей | 2026-05-18 |
| EmailRep + IPQS + GreyNoise + AbuseIPDB + Hunter | 2026-05-18 |
| NumVerify — обогащение телефона | 2026-05-18 |
