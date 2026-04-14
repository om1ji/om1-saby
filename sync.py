import logging
import sys
from datetime import datetime
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

from saby.db import get_db, init_db, save_document
from saby.main import DocumentsController, DocumentType, RequestsManager
from saby.models.upd import fetch_upd_document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.autoprihod.telegram import send_message

ALERT_CHAT_ID = 515588435
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs" / "saby_sync"


class TelegramAlertHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = f"🔴 <b>saby_sync</b>\n<code>{self.format(record)}</code>"
            send_message(text, chat_id=ALERT_CHAT_ID)
        except Exception:
            pass


def setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    tg_handler = TelegramAlertHandler()
    tg_handler.setLevel(logging.ERROR)
    tg_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

    log = logging.getLogger("saby_sync")
    log.setLevel(logging.DEBUG)
    log.addHandler(file_handler)
    log.addHandler(console_handler)
    log.addHandler(tg_handler)
    return log


logger = setup_logging()

SELLER_INN_MAPPING = {
    "7721844807":  "ООО «А.П.Р.»",
    "7712035729":  "НАО «АВТО-ЕВРО»",
    "5262337498":  "ООО «АВТОКОНТРАКТЫ»",
    "1655362290":  "ООО «ДИСТРИБЬЮТОРСКАЯ КОМПАНИЯ АВТОМИР»",
    "7728187283":  "ООО «АВТОРУСЬ ЛОГИСТИКА»",
    "7721568730":  "ООО «АВТОСТЭЛС»",
    "1656023236":  "ООО «АВТОХИМСЕРВИС»",
    "6678060382":  "ООО «АВТЭК»",
    "2540117060":  "ООО «АКИРА ОИЛ»",
    "1658101377":  "ООО «АРСЕНАЛ-АВТО»",
    "7723706908":  "ООО «БЕРГ ХОЛДИНГ»",
    "5401359124":  "ООО «ГРИНЛАЙТ»",
    "165707431570": "ИП Гареев Ян Линарович",
    "1657232793":  "ООО «ЕМЕХ-ТОТЕМ»",
    "5257140175":  "ООО «ИКСОРА»",
    "7840468492":  "ООО «ИНДАСТРИОИЛ»",
    "165113337206": "ИП Мустафина Альбина Мухлисовна",
    "7713442163":  "ООО «М ПАРТС»",
    "1660157105":  "ООО «МОСКВОРЕЧЬЕ-КАЗАНЬ»",
    "5257198376":  "ООО «ТОРГОВЫЙ ДОМ ИКСОРА»",
    "5259131585":  "ООО «ТОРГОВЫЙ ДОМ ПОВОЛЖЬЕ»",
    "3123430619":  "ООО «ТПЛ»",
    "1616011428":  "ООО «ТРАНЗИТ-ОЙЛ»",
    "1650131524":  "ООО «УПРАВЛЯЮЩАЯ КОМПАНИЯ ТРАНСТЕХСЕРВИС»",
    "7743666731":  "ООО «Ф.А. ЛОГИСТИК»",
    "7814558598":  "ООО «ФОРЕСТ»",
    "7720749068":  "ООО «ШАТЕ-М ПЛЮС»",
}

ALLOWED_SELLER_INNS = set(SELLER_INN_MAPPING)


def sync():
    load_dotenv()
    db = get_db()
    init_db(db)

    login = getenv("LOGIN")
    password = getenv("PASSWORD")

    date_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    date_to = datetime.now()

    logger.info("Синхронизация за %s — %s", date_from.date(), date_to.strftime("%H:%M"))

    saved = 0
    skipped = 0

    with RequestsManager(login, password) as mgr:
        docs = DocumentsController.get_documents(
            date_from, date_to, 100, mgr, doc_type=DocumentType.INCOMING
        )

        for doc in docs:
            upd = fetch_upd_document(doc.zip_link, mgr.session)
            if upd is None:
                logger.warning("Не удалось распарсить УПД для документа %s", doc.id)
                continue

            seller_inn = upd.seller.inn if upd.seller else None
            if seller_inn not in ALLOWED_SELLER_INNS:
                logger.info("Документ %s: поставщик %s (ИНН %s) не в whitelist, пропускаем", doc.id, upd.seller.name if upd.seller else "?", seller_inn)
                skipped += 1
                continue

            if save_document(db, doc, upd):
                saved += 1
            else:
                skipped += 1

    logger.info("Готово: сохранено %d, пропущено (дубли) %d", saved, skipped)


if __name__ == "__main__":
    sync()
