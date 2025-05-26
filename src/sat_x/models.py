import datetime

from sqlalchemy import DateTime, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_usage_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_temp_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    fan_speed_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Add other metrics like temperature if available via psutil or other libraries
    # temperature_celsius: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self):
        return f"<Metric(id={self.id}, timestamp={self.timestamp}, cpu={self.cpu_percent:.1f}%, temp={self.cpu_temp_celsius}°C, fan={self.fan_speed_percent}%)>"
