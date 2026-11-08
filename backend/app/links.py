from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .domain import Base, Entity


class StationGeography(Entity, Base):
    __tablename__ = "station_geography"
    station_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"), unique=True)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"))
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    local_name: Mapped[str | None]
    __table_args__ = (
        CheckConstraint(
            "(latitude IS NULL OR (latitude >= -90 AND latitude <= 90)) AND (longitude IS NULL OR (longitude >= -180 AND longitude <= 180))"
        ),
    )


class ServiceVehicle(Entity, Base):
    __tablename__ = "service_vehicles"
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), unique=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"))


class VariantStop(Entity, Base):
    __tablename__ = "route_variant_stops"
    variant_id: Mapped[str] = mapped_column(ForeignKey("route_variants.id"))
    stop_id: Mapped[str] = mapped_column(ForeignKey("route_stops.id"))
    __table_args__ = (UniqueConstraint("variant_id", "stop_id"),)
