from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Vessel(Base):
    __tablename__ = "vessels"
    id: Mapped[int] = mapped_column(primary_key=True)
    mmsi: Mapped[str] = mapped_column(String(9), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    vessel_type: Mapped[str | None] = mapped_column(String(50))
    flag: Mapped[str | None] = mapped_column(String(50))
    positions = relationship("Position", back_populates="vessel")


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"))
    latitude: Mapped[float]
    longitude: Mapped[float]
    speed_knots: Mapped[float | None]
    nav_status: Mapped[int | None]
    recorded_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    vessel = relationship("Vessel", back_populates="positions")


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"))
    alert_type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())