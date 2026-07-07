import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import EstadoSalaEnum
from app.database import Base
from app.models.usuario import Usuario


class Sala(Base):
    __tablename__ = "salas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    codigo: Mapped[str] = mapped_column(String(6), unique=True, index=True, nullable=False)
    estado: Mapped[EstadoSalaEnum] = mapped_column(
        Enum(
            EstadoSalaEnum,
            name="estado_sala_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=EstadoSalaEnum.ESPERANDO,
        server_default=EstadoSalaEnum.ESPERANDO.value,
    )
    anfitrion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    turno_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    jugadores: Mapped[list["SalaJugador"]] = relationship(
        back_populates="sala", cascade="all, delete-orphan"
    )


class SalaJugador(Base):
    __tablename__ = "sala_jugadores"
    __table_args__ = (UniqueConstraint("sala_id", "usuario_id", name="uq_sala_jugadores_sala_usuario"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    sala_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("salas.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    orden_turno: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    puntos: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    conectado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    unido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sala: Mapped["Sala"] = relationship(back_populates="jugadores")
    usuario: Mapped["Usuario"] = relationship()
