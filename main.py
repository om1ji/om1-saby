import requests
import io
import zipfile
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from datetime import datetime
from os import getenv
import logging
from dotenv import load_dotenv
from enum import StrEnum
from models.upd import MotorOilEntry

from models.document import Document
from models.upd import UPDDocument, parse_upd_xml

API_URL_BASE = "https://online.sbis.ru"
AUTH_API_URL = API_URL_BASE + "/auth/service/"
API_URL = API_URL_BASE + "/service/?srv=1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SABY Logger")


def fetch_upd_document(zip_url: str, session_id: str) -> UPDDocument:
    response = requests.get(zip_url, headers={"X-SBISSessionID": session_id})

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        xml_filename = next(name for name in z.namelist() if name.endswith(".xml"))
        xml_bytes = z.read(xml_filename)

    root: Element = ET.fromstring(xml_bytes.decode("windows-1251"))
    
    return parse_upd_xml(root)


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


class RequestsManager:
    _session = None

    def __init__(self, login: str, password: str):
        params = {
            "jsonrpc": "2.0",
            "method": "СБИС.Аутентифицировать",
            "params": {"Параметр": {"Логин": login, "Пароль": password}},
            "id": 0,
        }
        response = requests.post(AUTH_API_URL, json=params)
        self._session = response.json()["result"]
        logger.debug(f"Залогинились. Session ID: {self._session}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logout()
        return False

    def _logout(self):
        params = {"jsonrpc": "2.0", "method": "СБИС.Выход", "params": {}, "id": 0}
        requests.post(AUTH_API_URL, json=params, headers={"X-SBISSessionID": self._session})
        self._session = None
        logger.debug(f"Разлогинились. Session ID: {self._session}")

    @property
    def session(self) -> str:
        return self._session

    def request(self, method: str, params: dict, req_id: int = 1) -> dict:
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": req_id}
        logger.debug(f"Выполняю запрос {method}")

        try:
            response = requests.post(
                API_URL, json=payload, headers={"X-SBISSessionID": self._session}
            )
            return response.json()
        except requests.RequestException:
            logger.exception("При выполнении запроса произошла ошибка")
            raise


class DocumentsController:
    @staticmethod
    def get_documents(
        date_from: datetime,
        date_to: datetime,
        items_per_page: int,
        requests_manager: RequestsManager,
        doc_type: DocumentType = None,
    ) -> list[Document]:
        params = {
            "Фильтр": {
                "ДатаС": date_from.strftime("%d.%m.%Y"),
                "ДатаПо": date_to.strftime("%d.%m.%Y"),
                "Навигация": {"РазмерСтраницы": items_per_page},
            }
        }

        if doc_type is not None:
            params["Фильтр"]["Тип"] = doc_type
        else:
            raise ValueError("Укажите doc_type для поиска")

        response = requests_manager.request("СБИС.СписокДокументов", params)
        raw_docs = response["result"]["Документ"]
        return [Document.model_validate(doc) for doc in raw_docs]

def get_motor_oil_docs(manager: RequestsManager, date_from: datetime, date_to: datetime = None) -> list[MotorOilEntry]:
    if date_to is None:
        date_to = datetime.now()
        
    docs = DocumentsController.get_documents(date_from, date_to, 50, manager, doc_type=DocumentType.INCOMING)
    result = []

    for doc in docs:
        try:
            upd = fetch_upd_document(doc.zip_link, manager.session)

            if upd is None:
                logger.warning(f"УПД не удалось распарсить: {doc.zip_link}")
                continue

            for product in upd.products:
                if product.name and "масло" in product.name.lower():
                    result.append(MotorOilEntry(
                        doc_number=doc.number,
                        article=product.article,
                        name=product.name,
                        marking_code=product.marking_code,
                    ))

        except Exception:
            logger.exception("Ошибка чтения УПД из XML-документа")

    return result

def main():
    load_dotenv()

    login = getenv("LOGIN")
    password = getenv("PASSWORD")

    with RequestsManager(login, password) as mgr:
        date_from = datetime(2026, 3, 1)
        
        oil_docs = get_motor_oil_docs(mgr, date_from)
        
        print(oil_docs)
        
""" MotorOilEntry(doc_number='УАК1671.../1',
            article='...',
            name='Масло моторное ...',
            marking_code=GS1Code(gtin='...',
                                serial='...',
                                session_key=None,
                                signature=None)),
"""

if __name__ == "__main__":
    main()
