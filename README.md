# Om1-Saby - обёртка над Saby API

Saby (ex. СБИС) - ЭДО

### Функционал

На данный момент обёртка умеет читать документы и парсить УПД. Из УПД парсить коды маркировки (КМ) в формате GS1 DataMatrix. Обёртка была написана с целью автоматизировать дальнешее оприходование маркированных товаров.

### Начало работы

В файле `.env` добавить следующие значения:

- `LOGIN` - логин от учётной записи Saby
- `PASSWORD` - пароль от учётной записи Saby

### Запуск

Запускать командой: 
```bash
python3 main.py
```

или 

```bash
uv run main.py
```

### Основные методы

```python
def main():
    login = os.getenv("LOGIN")
    password = os.getenv("PASSWORD")

    # Менеджер запросов на API
    with RequestsManager(login, password) as mgr:
        date_from = datetime(2026, 3, 15)
        date_to = datetime(2026, 3, 16)

        # Обязательно выбрать тип документа из enum DocumentType
        doc_type = DocumentType.INCOMING

        # Собрать все документы
        docs = DocumentsController.get_documents(date_from, date_to, 50, mgr, doc_type=doc_type)

        for doc in docs:
            upd = fetch_upd_document(doc.zip_link, mgr.session)

            # В каждом УПД отобразить названия товаров
            for product in upd.products:
                print(product.name)
```

### Типы документов

```python
class DocumentType(StrEnum):
    INCOMING = "ДокОтгрВх"        # Приход (Поступление)
    OUTGOING = "ДокОтгрИсх"       # Расход (Реализация)
    INVOICE_IN = "ФактураВх"       # Счет-фактура входящий
    INVOICE_OUT = "ФактураИсх"     # Счет-фактура исходящий
    ORDER_IN = "ЗаказВх"           # Заказ входящий
    ORDER_OUT = "ЗаказИсх"         # Заказ исходящий
    CONTRACT_IN = "ДоговорВх"      # Договор входящий
    CONTRACT_OUT = "ДоговорИсх"    # Договор исходящий
    BILL_IN = "СчетВх"             # Счет входящий
    BILL_OUT = "СчетИсх"           # Счет исходящий
    RETURN_IN = "ReturnIn"         # Возврат от покупателя
    RETURN_OUT = "ReturnOut"       # Возврат поставщику
    CORRECTION_IN = "CorrIn"       # Корректировка входящая
    CORRECTION_OUT = "CorrOut"     # Корректировка исходящая
```
