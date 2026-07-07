import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import EstadoRondaEnum, PrediccionEnum, ResultadoEnum
from app.database import Base
from app.models.pregunta import Pregunta


class Ronda(Base):
    __tablename__ = "rondas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    sala_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("salas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    pregunta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("preguntas.id"), nullable=False
    )
    lector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    prediccion: Mapped[PrediccionEnum | None] = mapped_column(
        Enum(
            PrediccionEnum,
            name="prediccion_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    estado: Mapped[EstadoRondaEnum] = mapped_column(
        Enum(
            EstadoRondaEnum,
            name="estado_ronda_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=EstadoRondaEnum.LEYENDO,
        server_default=EstadoRondaEnum.LEYENDO.value,
    )
    resultado: Mapped[ResultadoEnum | None] = mapped_column(
        Enum(
            ResultadoEnum,
            name="resultado_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    acierto: Mapped[bool | None] = mapped_column(nullable=True)

    votos: Mapped[list["Voto"]] = relationship(back_populates="ronda", cascade="all, delete-orphan")
    pregunta: Mapped["Pregunta"] = relationship()


class Voto(Base):
    __tablename__ = "votos"
    __table_args__ = (
        CheckConstraint("opcion IN (1, 2)", name="ck_votos_opcion"),
        UniqueConstraint("ronda_id", "usuario_id", name="uq_votos_ronda_usuario"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    ronda_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rondas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    opcion: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    ronda: Mapped["Ronda"] = relationship(back_populates="votos")
