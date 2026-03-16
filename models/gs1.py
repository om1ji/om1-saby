from dataclasses import dataclass
from typing import Optional

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

def parse_gs1(raw: bytes) -> GS1Code:
    # Убираем завершающие \r
    data = raw.rstrip(b"\r")
    # Разбиваем по разделителю групп GS (\x1d)
    groups = data.split(b"\x1d")

    result = {}
    for group in groups:
        text = group.decode("ascii")
        ai = text[:2]
        value = text[2:]
        result[ai] = value

    # AI 01 — GTIN (14 символов), AI 21 — серийный номер
    block_01_21 = result.get("01", "")
    gtin = block_01_21[:14]
    serial = block_01_21[14:] if len(block_01_21) > 14 else ""

    # Если serial не нашли через первый блок — ищем AI 21 отдельно
    if not serial and "21" in result:
        serial = result["21"]

    return GS1Code(
        gtin=gtin,
        serial=serial,
        session_key=result.get("91"),
        signature=result.get("92"),
    )