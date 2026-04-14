# saby-api-wrapper

> Python-обёртка над [Saby (СБИС)](https://saby.ru/) API для работы с ЭДО: получение документов, парсинг УПД и извлечение кодов маркировки GS1 DataMatrix.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Возможности

- Аутентификация и управление сессией через Saby API (JSONRPC)
- Получение списка документов с фильтрацией по типу и периоду
- Скачивание и парсинг УПД из ZIP-архивов (XML, кодировка Windows-1251)
- Декодирование кодов маркировки в формате GS1 DataMatrix (AI 01/21/91/92)
- Конвертация GTIN-14 → EAN-13
- Pydantic-модели для всех структур данных

## Требования

- Python 3.10+
- Аккаунт в системе Saby (СБИС) с доступом к API

## Установка

```bash
# Через uv (рекомендуется)
uv sync

# Или через pip
pip install -r requirements.txt
```

## Конфигурация

Создайте файл `.env` в корне проекта:

```env
LOGIN=ваш_логин
PASSWORD=ваш_пароль
```

## Использование

### Быстрый старт

```bash
uv run main.py
# или
python main.py
```

### В коде

```python
from datetime import datetime
from main import RequestsManager, DocumentsController, DocumentType, get_motor_oil_docs

with RequestsManager(login, password) as mgr:
    # Получить все входящие документы за март 2026
    docs = DocumentsController.get_documents(
        date_from=datetime(2026, 3, 1),
        date_to=datetime(2026, 3, 31),
        items_per_page=50,
        requests_manager=mgr,
        doc_type=DocumentType.INCOMING,
    )

    # Извлечь коды маркировки моторных масел
    oil_entries = get_motor_oil_docs(mgr, date_from=datetime(2026, 3, 1))
    for entry in oil_entries:
        print(entry.name, entry.marking_code.short_code)
```

### Пример результата `get_motor_oil_docs`

```python
MotorOilEntry(
    doc_number='УАК1671.../1',
    article='12345',
    name='Масло моторное Castrol EDGE 5W-30',
    marking_code=GS1Code(
        gtin='04607085550123',
        serial='ABCxyz123',
        session_key='abc123',
        signature=None,
    )
)
```

## Интеграция с sk_auto1 (ЭДО СБИС → АвтоДилер)

Модуль используется в проекте **sk_auto1** как источник данных электронного документооборота (ЭДО) СБИС для автоматического обновления номенклатуры в ERP АвтоДилер.

**Поток данных:**
```
[ЭДО СБИС] → sync.py (каждые 15 мин) → [MongoDB: saby.documents]
                                                  ↓
                          scripts/autoprihod/utils/saby_import.py
                                                  ↓
                              Firebird (SHOP_NOMENCLATURE, DOCUMENT_IN)
```

**`sync.py`** — забирает входящие УПД за текущий день, сохраняет в MongoDB. Запускается через Планировщик задач Windows каждые 15 минут. Дедупликация по `saby_id` — повторная загрузка одного документа безопасна.

**`db.py`** — CRUD для MongoDB: сохранение документов, получение необработанных, отметка об обработке.

**`saby_import.py`** (в `scripts/autoprihod/utils/`) — читает необработанные документы из MongoDB и:
- Создаёт/находит номенклатуру в `SHOP_NOMENCLATURE`
- Для товаров с кодом маркировки GS1 DataMatrix записывает EAN-13 в `BAR_CODE` и проставляет признак маркировки

## Структура проекта

```
├── main.py               # RequestsManager (авторизация), DocumentsController
├── sync.py               # Polling-сервис: Saby → MongoDB
├── db.py                 # CRUD для MongoDB (коллекция documents)
├── models/
│   ├── document.py       # Pydantic-модели документов СБИС
│   └── upd.py            # Pydantic-модели и парсер УПД (XML), GS1Code
├── requirements.txt
└── .env                  # Не коммитить
```

## Типы документов

| Константа | Значение | Описание |
|---|---|---|
| `DocumentType.INCOMING` | `ДокОтгрВх` | Приход (Поступление) |
| `DocumentType.OUTGOING` | `ДокОтгрИсх` | Расход (Реализация) |
| `DocumentType.INVOICE_IN` | `ФактураВх` | Счёт-фактура входящий |
| `DocumentType.INVOICE_OUT` | `ФактураИсх` | Счёт-фактура исходящий |
| `DocumentType.ORDER_IN` | `ЗаказВх` | Заказ входящий |
| `DocumentType.ORDER_OUT` | `ЗаказИсх` | Заказ исходящий |
| `DocumentType.BILL_IN` | `СчетВх` | Счёт входящий |
| `DocumentType.BILL_OUT` | `СчетИсх` | Счёт исходящий |
| `DocumentType.RETURN_IN` | `ReturnIn` | Возврат от покупателя |
| `DocumentType.RETURN_OUT` | `ReturnOut` | Возврат поставщику |
| `DocumentType.CORRECTION_IN` | `CorrIn` | Корректировка входящая |
| `DocumentType.CORRECTION_OUT` | `CorrOut` | Корректировка исходящая |

## Структура `GS1Code`

| Поле | AI | Описание |
|---|---|---|
| `gtin` | `01` | GTIN-14 товара |
| `serial` | `21` | Серийный номер |
| `session_key` | `91` | Ключ сессии (опционально) |
| `signature` | `92` | Подпись (опционально) |
| `.short_code` | — | Код в формате `01{gtin}21{serial}` |
| `.ean13` | — | EAN-13 из GTIN-14 (убирает ведущий `0`) |

## Вклад в проект

Будем рады pull request'ам. Пожалуйста:

1. Форкните репозиторий
2. Создайте ветку: `git checkout -b feature/my-feature`
3. Закоммитьте изменения: `git commit -m 'Add my feature'`
4. Откройте Pull Request

## Лицензия

MIT
