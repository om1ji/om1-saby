import pydantic
from datetime import datetime
from typing import Optional


class MarkingState(pydantic.BaseModel):
    operation_code: str = pydantic.Field(alias="КодОперации")
    operation_state_code: str = pydantic.Field(alias="КодСостоянияОперации")
    operation_name: str = pydantic.Field(alias="Операция")
    operation_state_name: str = pydantic.Field(alias="СостояниеОперации")


class DocumentExtension(pydantic.BaseModel):
    archived: str = pydantic.Field(alias="Архивирован")
    immutable: str = pydantic.Field(alias="ЗакрытОтИзменений")
    marking: Optional[str] = pydantic.Field(alias="Маркировка", default=None)
    plus_mark: str = pydantic.Field(alias="ОтметкаПлюсом")
    marking_state: Optional[MarkingState] = pydantic.Field(alias="СостояниеМарк", default=None)


class DocumentState(pydantic.BaseModel):
    code: str = pydantic.Field(alias="Код")
    name: str = pydantic.Field(alias="Название")
    description: str = pydantic.Field(alias="Описание")
    comment: str = pydantic.Field(alias="Примечание")


class DocumentReglament(pydantic.BaseModel):
    id: str = pydantic.Field(alias="Идентификатор")
    name: str = pydantic.Field(alias="Название")


class LegalEntity(pydantic.BaseModel):
    inn: str = pydantic.Field(alias="ИНН")
    kpp: str = pydantic.Field(alias="КПП")
    name: str = pydantic.Field(alias="Название")
    full_name: str = pydantic.Field(alias="НазваниеПолное")
    address: str = pydantic.Field(alias="АдресЮридический")


class Counterparty(pydantic.BaseModel):
    type: str = pydantic.Field(alias="Тип")
    legal_entity: Optional[LegalEntity] = pydantic.Field(alias="СвЮЛ", default=None)


class Document(pydantic.BaseModel):
    id: str = pydantic.Field(alias="Идентификатор")
    date: datetime = pydantic.Field(alias="Дата")
    number: str = pydantic.Field(alias="Номер")
    name: str = pydantic.Field(alias="Название")
    comment: str = pydantic.Field(alias="Примечание")
    created_at: datetime = pydantic.Field(alias="ДатаВремяСоздания")
    type: str = pydantic.Field(alias="Тип")
    subtype: str = pydantic.Field(alias="Подтип")
    direction: str = pydantic.Field(alias="Направление")
    sum: str = pydantic.Field(alias="Сумма")
    deadline: str = pydantic.Field(alias="Срок")
    deleted: str = pydantic.Field(alias="Удален")
    extension: DocumentExtension = pydantic.Field(alias="Расширение")
    state: DocumentState = pydantic.Field(alias="Состояние")
    reglament: DocumentReglament = pydantic.Field(alias="Регламент")
    counterparty: Counterparty = pydantic.Field(alias="Контрагент")
    pdf_link: str = pydantic.Field(alias="СсылкаНаPDF")
    zip_link: str = pydantic.Field(alias="СсылкаНаАрхив")

    model_config = pydantic.ConfigDict(populate_by_name=True)

    @pydantic.field_validator("date", "created_at", mode="before")
    @classmethod
    def parse_date(cls, value: str) -> datetime:
        # API возвращает два формата: "15.03.2026" и "15.03.2026 14.23.05"
        for fmt in ("%d.%m.%Y %H.%M.%S", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValueError(f"Не удалось распознать дату: {value}")
