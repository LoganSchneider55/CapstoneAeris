from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Float, Integer, BigInteger, Boolean, ForeignKey, UniqueConstraint, Index
from datetime import datetime


class Base(DeclarativeBase):
    pass

class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

class APIKey(Base):
    __tablename__ = "api_keys"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner: Mapped[str] = mapped_column(String(128))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))

class PollutantThreshold(Base):
    __tablename__ = "pollutant_thresholds"
    sensor_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    warn: Mapped[float]
    danger: Mapped[float]

class Reading(Base):
    __tablename__ = "readings"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), ForeignKey("devices.device_id"))
    sensor_type: Mapped[str] = mapped_column(String(32))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    value: Mapped[float]
    aqi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alert_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    api_key: Mapped[str | None] = mapped_column(String(64), ForeignKey("api_keys.key"), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("device_id", "sensor_type", "measured_at", name="uq_reading"),
        Index("idx_readings_device_type_time", "device_id", "sensor_type", "measured_at"),
        Index("idx_readings_alert", "alert_flag", "measured_at"),
    )
