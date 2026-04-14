"""Отображает все документы из MongoDB в читаемом виде."""
from pymongo import MongoClient, ASCENDING

from saby.sync import SELLER_INN_MAPPING

client = MongoClient("mongodb://localhost:27017")
db = client["saby"]

docs = list(db["documents"].find().sort("date", ASCENDING))

if not docs:
    print("База данных пуста.")
else:
    print(f"Всего документов: {len(docs)}\n")
    print("=" * 70)

    for doc in docs:
        seller_inn = doc.get("seller_inn", "—")
        seller_name = SELLER_INN_MAPPING.get(seller_inn, "Неизвестный поставщик")
        data = doc.get("data") or {}
        products = data.get("products") or []
        processed = "✓" if doc.get("processed") else "○"
        date = doc.get("date")
        date_str = date.strftime("%d.%m.%Y") if date else "—"

        print(f"  {processed}  {date_str}  │  {seller_name}  (ИНН {seller_inn})")
        print(f"      Saby ID: {doc.get('saby_id', '—')}")
        print(f"      Номер:   {data.get('number', '—')}")
        print(f"      Товаров: {len(products)}")

        for p in products:
            article = p.get("article") or "—"
            name = p.get("name") or "—"
            brand = p.get("manufacturer") or "—"
            price = p.get("price") or 0
            qty = p.get("quantity") or "—"
            marking_code = p.get("marking_code")
            has_gs1 = "🏷" if marking_code else "  "
            print(f"        {has_gs1} {article:<20} {brand:<15} {name[:30]:<30} {qty} шт.  {price} ₽")
            if isinstance(marking_code, dict):
                gtin = marking_code.get("gtin", "")
                ean13 = gtin[1:] if len(gtin) == 14 and gtin.startswith("0") else None
                print(f"             GTIN: {gtin}  →  EAN-13: {ean13 or '(не удалось извлечь)'}")

        print("-" * 70)

print("\n🏷  — есть GS1-код маркировки   ✓ — обработан   ○ — не обработан")
