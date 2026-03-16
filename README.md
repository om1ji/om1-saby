# Om1-Saby — обёртка над Saby API

Saby (ex. СБИС) — система ЭДО. Обёртка умеет читать входящие документы, парсить УПД и извлекать коды маркировки (КМ) в формате GS1 DataMatrix. Написана для автоматизации оприходования маркированных товаров.

## Установка
```bash
uv sync
# или
pip install -r requirements.txt
```

## Начало работы

Создайте файл `.env` со следующими значениями:
```env
LOGIN=ваш_логин
PASSWORD=ваш_пароль
```

## Запуск
```bash
uv run main.py
# или
python3 main.py
```

## Структура проекта
```
├── main.py
├── models/
│   ├── document.py   # Модели документов СБИС
│   └── upd.py        # Модели и парсер УПД (XML)
└── .env
```

## Пример использования
```python
def main():
    login = getenv("LOGIN")
    password = getenv("PASSWORD")

    with RequestsManager(login, password) as mgr:
        date_from = datetime(2026, 3, 1)
        
        oil_docs = get_motor_oil_docs(mgr, date_from)
        
        print(oil_docs)

# Экземпляр из oil_docs     
MotorOilEntry(doc_number='УАК1671.../1',
        article='...',
        name='Масло моторное ...',
        marking_code=GS1Code(gtin='...',
                            serial='...',
                            session_key=None,
                            signature=None))
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