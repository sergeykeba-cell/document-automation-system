# 📋 Система автоматизации документооборота

> Веб-система для поиска сотрудников по базе данных и автоматической генерации PDF-документов (направлений, характеристик, рапортов) с ведением реестра.

Разработана с использованием **Claude AI** как основного инструмента разработки — от проектирования архитектуры до написания кода и отладки.

---

## ✨ Возможности

- 🔍 **Живой поиск** по ФИО или номеру телефона (29 000+ записей)
- 📄 **Генерация 5 типов документов** в PDF с кириллицей
- 📊 **Импорт данных** из Excel (.xls / .xlsx) с автодедупликацией
- 📂 **Реестр документов** — история по каждому типу, экспорт в .xlsx
- 👥 **Роли пользователей** — admin / operator
- 📝 **Аудит-лог** — кто, когда, что создал
- ⚡ **Версионирование файлов** — повторное создание не перезаписывает старое

---

## 🛠 Стек

| Слой | Технология |
|------|-----------|
| Backend | Python 3.11 · FastAPI · SQLite (WAL) |
| Данные | pandas · openpyxl · xlrd |
| PDF | reportlab |
| Auth | HTTP Basic Auth · bcrypt |
| Frontend | Vanilla HTML/CSS/JS (single file, no framework) |

---

## 🚀 Быстрый старт

### Windows

```bash
start.bat
```

### Linux / macOS

```bash
chmod +x start.sh && ./start.sh
```

Открыть браузер: **http://localhost:8000**

Скрипты автоматически:
1. Создают виртуальное окружение
2. Устанавливают зависимости
3. Запускают сервер

---

## 📦 Ручная установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

# 2. Создать виртуальное окружение (Python 3.11)
py -3.11 -m venv .venv          # Windows
python3.11 -m venv .venv        # Linux/macOS

# 3. Активировать
.venv\Scripts\activate           # Windows
source .venv/bin/activate        # Linux/macOS

# 4. Установить зависимости
pip install -r requirements.txt

# 5. Запустить
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔐 Первый вход

При первом запуске автоматически создаются два пользователя:

| Логин | Пароль | Роль | Доступ |
|-------|--------|------|--------|
| `admin` | `admin123` | admin | всё, включая импорт и экспорт |
| `operator` | `op123` | operator | поиск и создание документов |

> ⚠️ **Смените пароли** после первого входа:
> ```bash
> python -c "from app.security import create_user; create_user('admin','НовыйПароль','admin')"
> ```

---

## 📥 Импорт данных из Excel

1. Файл должен содержать лист с именем **СЗЧ**
2. Обязательные колонки: `П.І.Б.`, `Номер телефону`
3. Остальные читаются автоматически (нечёткое сопоставление названий):

| Колонка в Excel | Поле |
|----------------|------|
| П.І.Б. | ФИО |
| Номер телефону | Телефон (нормализуется автоматически) |
| військове звання | Звание |
| Дата народження | Дата рождения |
| Розміщена о/с | Размещение |
| підрозділ | Подразделение |
| Прибув у В/Ч | Дата прибытия |
| Дата зарахування у В/Ч А7020 | Дата зачисления |

> Лишние 30+ колонок игнорируются. Дубликаты определяются по ФИО + дата рождения + телефон.

**Диагностика** (если данные не читаются):
```
POST /api/import/preview
```
Вернёт точный маппинг колонок и пример первой строки — без записи в БД.

---

## 📁 Структура проекта

```
├── app/
│   ├── main.py             # FastAPI — все эндпоинты
│   ├── database.py         # SQLite + схема + WAL
│   ├── security.py         # Basic Auth + bcrypt + роли
│   ├── import_service.py   # Импорт Excel, нормализация, UPSERT
│   ├── pdf_gen.py          # Генерация PDF (reportlab + кириллица)
│   ├── export_service.py   # Экспорт реестра → .xlsx
│   └── static/
│       └── index.html      # Весь UI в одном файле
├── pdfs/                   # Сгенерированные PDF (ДАТА/ФИО_тип.pdf)
├── database.db             # SQLite (создаётся автоматически)
├── FreeSans.ttf            # Шрифт с кириллицей для PDF
├── requirements.txt
├── start.bat               # Запуск Windows
└── start.sh                # Запуск Linux/macOS
```

---

## 🌐 API

Интерактивная документация: **http://localhost:8000/docs**

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `/api/health` | all | Статус + количество записей |
| GET | `/api/search?mode=pib\|phone&q=` | all | Поиск |
| POST | `/api/documents` | all | Создать документ + PDF |
| GET | `/api/registry?doc_type=` | all | Реестр направлений |
| GET | `/api/files/{doc_id}` | all | Скачать PDF |
| POST | `/api/import` | admin | Импорт .xls |
| POST | `/api/import/preview` | admin | Диагностика колонок |
| GET | `/api/export?doc_type=` | admin | Экспорт реестра → .xlsx |
| GET | `/api/audit` | admin | Журнал действий |

---

## 🖋 Кириллица в PDF

Положить **FreeSans.ttf** или **DejaVuSans.ttf** в корень проекта.

**Ubuntu/Debian:**
```bash
sudo apt install fonts-freefont-ttf
cp /usr/share/fonts/truetype/freefont/FreeSans.ttf ./
```

**Windows:** скопировать любой TTF с кириллицей из `C:\Windows\Fonts\`.

Если шрифт не найден — PDF генерируется с Helvetica (без кириллицы).

---

## 💾 Резервное копирование

```bash
# Ручной бэкап
cp database.db backups/database_$(date +%Y%m%d).db

# Автоматически каждый день (Linux cron)
0 3 * * * cp /path/to/database.db /path/to/backups/db_$(date +\%Y\%m\%d).db
```

---

## 🤖 О разработке

Проект разработан с применением **AI-assisted development**:

- Проектирование архитектуры и схемы БД совместно с Claude AI
- Генерация и итеративное улучшение кода через prompt engineering
- Отладка, валидация и ревью AI-сгенерированного кода вручную
- Полный цикл: требование → схема → код → тест → фикс через диалог с AI

**Инструменты:** Claude (Anthropic) · Python 3.11 · FastAPI · SQLite

---

## 📄 Лицензия

MIT
