import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import requests
import io
import zipfile

import pydantic

logger = logging.getLogger(__name__)


@dataclass
class GS1Code:
    gtin: str
    serial: str
    session_key: Optional[str] = None
    signature: Optional[str] = None

    @property
    def short_code(self) -> str:
        """Код в формате СБИС/ЧЗ: первые 31 символ без разделителей"""
        return f"01{self.gtin}21{self.serial}"

    @property
    def ean13(self) -> str | None:
        """Конвертирует GTIN-14 в EAN-13, убирая ведущий ноль"""
        if len(self.gtin) == 14 and self.gtin.startswith("0"):
            return self.gtin[1:]
        return None


@dataclass
class MotorOilEntry:
    doc_number: str
    article: str | None
    name: str
    marking_code: GS1Code | None


def parse_gs1(raw: str) -> GS1Code:
    # Убираем завершающие \r
    data = raw.rstrip("\r")
    # Разбиваем по разделителю групп GS (\x1d)
    groups = data.split("\x1d")

    result = {}
    for group in groups:
        ai = group[:2]
        value = group[2:]
        result[ai] = value

    # AI 01 — GTIN (14 символов), AI 21 — серийный номер
    block_01_21 = result.get("01", "")
    gtin = block_01_21[:14]
    serial = block_01_21[14:] if len(block_01_21) > 14 else ""

    if not serial and "21" in result:
        serial = result["21"]

    return GS1Code(
        gtin=gtin,
        serial=serial,
        session_key=result.get("91"),
        signature=result.get("92"),
    )


class FullName(pydantic.BaseModel):
    last_name: str | None
    first_name: str | None
    middle_name: str | None


class BankDetails(pydantic.BaseModel):
    account_number: str | None
    bank_name: str | None
    bik: str | None
    cor_account: str | None


class LegalEntity(pydantic.BaseModel):
    name: str | None
    inn: str | None
    kpp: str | None


class IndividualEntrepreneur(pydantic.BaseModel):
    inn: str | None
    full_name: FullName | None


class UPDProduct(pydantic.BaseModel):
    row_number: int | None
    name: str | None
    article: str | None
    manufacturer: str | None
    unit_code: int | None
    unit_name: str | None
    quantity: float | None
    price: float | None
    sum_without_vat: float | None
    vat_rate: str | None
    sum_with_vat: float | None
    vat_sum: float | None = None
    marking_code: str | GS1Code | None = None  # КИЗ


class UPDTotals(pydantic.BaseModel):
    sum_without_vat: str | None
    sum_with_vat: str | None
    vat_sum: str | None


class UPDDocument(pydantic.BaseModel):
    number: str | None
    date: datetime | None
    seller: LegalEntity | None
    buyer: IndividualEntrepreneur | None
    products: list[UPDProduct] | None
    totals: UPDTotals | None
    function: str | None  # СЧФ / ДОП / СЧФДОП


def parse_upd_xml(root: ET.Element) -> UPDDocument | None:
    doc = root.find("Документ")

    if doc is None:
        logging.debug("Нет тега <Документ>")
        return None

    # Проверяем что это УПД, а не служебный документ
    if doc.find("ТаблСчФакт") is None:
        logging.debug("Нет тега <ТаблСчФакт>")
        return None

    try:
        sf = doc.find("СвСчФакт")

        # Продавец
        seller_el = sf.find("СвПрод/ИдСв/СвЮЛУч")
        seller = LegalEntity(
            name=seller_el.get("НаимОрг"),
            inn=seller_el.get("ИННЮЛ"),
            kpp=seller_el.get("КПП"),
        )

        # Покупатель (ИП)
        buyer_ip = sf.find("СвПокуп/ИдСв/СвИП")
        buyer_fio = buyer_ip.find("ФИО")
        buyer = IndividualEntrepreneur(
            inn=buyer_ip.get("ИННФЛ"),
            full_name=FullName(
                last_name=buyer_fio.get("Фамилия"),
                first_name=buyer_fio.get("Имя"),
                middle_name=buyer_fio.get("Отчество"),
            ),
        )

        # Товары
        products = []
        for item in doc.findall("ТаблСчФакт/СведТов"):
            raw_name = item.get("НаимТов", "").strip()
            manufacturer = None

            if "||" in raw_name:
                parts = raw_name.split("||")
                name = parts[1].strip()
                manufacturer = parts[2].strip() if len(parts) > 2 else None
            else:
                name = raw_name

            dop_sved = item.find("ДопСведТов")
            article = dop_sved.get("КодТов") if dop_sved is not None else None

            kiz_raw = item.find("ДопСведТов/НомСредИдентТов/КИЗ")
            kiz = parse_gs1(kiz_raw.text) if kiz_raw is not None and kiz_raw.text else None

            vat_el = item.find("СумНал/СумНал")

            products.append(UPDProduct(
                row_number=int(item.get("НомСтр")),
                name=name,
                article=article,
                manufacturer=manufacturer,
                unit_code=item.get("ОКЕИ_Тов"),
                unit_name=item.get("НаимЕдИзм"),
                quantity=float(item.get("КолТов") or 0),
                price=item.get("ЦенаТов") or None,
                sum_without_vat=float(item.get("СтТовБезНДС")),
                vat_rate=item.get("НалСт"),
                sum_with_vat=float(item.get("СтТовУчНал")),
                vat_sum=vat_el.text if vat_el is not None else None,
                marking_code=kiz,
            ))

        # Итоги
        totals_el = doc.find("ТаблСчФакт/ВсегоОпл")
        vat_total_el = totals_el.find("СумНалВсего/СумНал")
        totals = UPDTotals(
            sum_without_vat=totals_el.get("СтТовБезНДСВсего"),
            sum_with_vat=totals_el.get("СтТовУчНалВсего"),
            vat_sum=vat_total_el.text,
        )

        return UPDDocument(
            number=sf.get("НомерДок"),
            date=datetime.strptime(sf.get("ДатаДок"), "%d.%m.%Y"),
            seller=seller,
            buyer=buyer,
            products=products,
            totals=totals,
            function=doc.get("Функция"),
        )
    except AttributeError:
        logger.exception("Ошибка парсинга УПД XML:\n%s", ET.tostring(root, encoding="unicode"))
        return None


def fetch_upd_document(zip_url: str, session_id: str) -> UPDDocument | None:
    response = requests.get(zip_url, headers={"X-SBISSessionID": session_id})

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        xml_filename = next(name for name in z.namelist() if name.endswith(".xml"))
        xml_bytes = z.read(xml_filename)

    root: ET.Element = ET.fromstring(xml_bytes.decode("windows-1251"))

    return parse_upd_xml(root)