import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pregunta(Base):
    __tablename__ = "preguntas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    enunciado: Mapped[str] = mapped_column(Text, nullable=False)
    # Borrado suave: una pregunta ya jugada no puede borrarse físicamente porque
    # rondas.pregunta_id la referencia (historial y rondas activas); se marca y se
    # oculta del listado y del mazo en su lugar.
    eliminada: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=text("false")
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    opciones: Mapped[list["Opcion"]] = relationship(
        back_populates="pregunta", cascade="all, delete-orphan", order_by="Opcion.numero"
    )


class Opcion(Base):
    __tablename__ = "opciones"
    __table_args__ = (
        CheckConstraint("numero IN (1, 2)", name="ck_opciones_numero"),
        UniqueConstraint("pregunta_id", "numero", name="uq_opciones_pregunta_numero"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    pregunta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("preguntas.id", ondelete="CASCADE"), nullable=False
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)

    pregunta: Mapped["Pregunta"] = relationship(back_populates="opciones")
