import logging
from datetime import datetime
from os import getenv

import requests
from dotenv import load_dotenv
from enum import StrEnum

from saby.models.document import Document
from saby.models.upd import fetch_upd_document, UPDDocument

API_URL_BASE = "https://online.sbis.ru"
AUTH_API_URL = API_URL_BASE + "/auth/service/"
API_URL = API_URL_BASE + "/service/?srv=1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SABY Logger")


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
        response_json = response.json()

        try:
            if "error" in response_json:
                logger.error(response_json["error"]["message"])    

            self._session = response_json["result"]          

        except KeyError:
            logger.exception("Нет поля result при попытке авторизоваться")
            
            
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
        doc_type: DocumentType | None = None,
    ) -> list[Document]:
        if doc_type is None:
            raise ValueError("Укажите doc_type для поиска")

        params = {
            "Фильтр": {
                "ДатаС": date_from.strftime("%d.%m.%Y"),
                "ДатаПо": date_to.strftime("%d.%m.%Y"),
                "Тип": doc_type,
                "Навигация": {"РазмерСтраницы": items_per_page},
            }
        }

        response = requests_manager.request("СБИС.СписокДокументов", params)
        raw_docs = response["result"]["Документ"]
        return [Document.model_validate(doc) for doc in raw_docs]

    def get_incoming_documents(
        date_from: datetime,
        date_to: datetime,
        items_per_page: int,
        requests_manager: RequestsManager,
        ) -> list[UPDDocument]:
        docs = DocumentsController.get_documents(date_from, date_to, items_per_page, requests_manager, DocumentType.INCOMING)
        
        result = []
        
        for doc in docs:
            upd = fetch_upd_document(doc.zip_link, requests_manager._session) 
            
            if upd is not None:
                result.append(upd)
                
        return result


def main():
    load_dotenv()

    login = getenv("LOGIN")
    password = getenv("PASSWORD")

    with RequestsManager(login, password) as mgr:
        date_from = datetime(2026, 3, 17)
        
        docs = DocumentsController.get_incoming_documents(date_from, datetime.now(), 50, mgr)

        for doc in docs:
            print(doc.model_dump_json())

if __name__ == "__main__":
    main()
