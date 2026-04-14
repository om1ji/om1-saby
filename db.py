import logging
from datetime import datetime

from pymongo import MongoClient, ASCENDING
from pymongo.database import Database

from .models.document import Document
from .models.upd import UPDDocument

logger = logging.getLogger(__name__)

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "saby"


def get_db(uri: str = MONGO_URI) -> Database:
    client = MongoClient(uri)
    return client[DB_NAME]


def init_db(db: Database) -> None:
    db["documents"].create_index("saby_id", unique=True)
    db["documents"].create_index("processed")
    db["documents"].create_index("seller_inn")
    logger.debug("Индексы MongoDB созданы")


def save_document(db: Database, doc: Document, upd: UPDDocument) -> bool:
    """Сохраняет документ. Возвращает True если документ новый."""
    existing = db["documents"].find_one({"saby_id": doc.id}, {"_id": 1})
    if existing:
        logger.debug("Документ %s уже в БД, пропускаем", doc.id)
        return False

    db["documents"].insert_one({
        "saby_id": doc.id,
        "seller_inn": upd.seller.inn if upd.seller else None,
        "date": upd.date,
        "processed": False,
        "fetched_at": datetime.now(),
        "data": upd.model_dump(mode="json"),
    })

    logger.debug("Сохранён документ %s", doc.id)
    return True



def get_unprocessed_documents(db: Database) -> list[dict]:
    return list(
        db["documents"].find({"processed": False}).sort("date", ASCENDING)
    )


def mark_document_processed(db: Database, saby_id: str) -> None:
    db["documents"].update_one(
        {"saby_id": saby_id},
        {"$set": {"processed": True}},
    )
    logger.debug("Документ %s помечен как обработанный", saby_id)
