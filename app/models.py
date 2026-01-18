from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    platform = Column(String, nullable=False, default="ios")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    safezones = relationship("SafeZone", back_populates="device", cascade="all, delete-orphan")
    locations = relationship("LocationEvent", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("AlertEvent", back_populates="device", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="device", cascade="all, delete-orphan")
    tokens = relationship("DeviceToken", back_populates="device", cascade="all, delete-orphan")
    subscriptions_owned = relationship(
        "Subscription",
        foreign_keys="Subscription.owner_device_id",
        back_populates="owner_device",
        cascade="all, delete-orphan",
    )
    subscriptions_subscribed = relationship(
        "Subscription",
        foreign_keys="Subscription.subscriber_device_id",
        back_populates="subscriber_device",
        cascade="all, delete-orphan",
    )
    invitations = relationship("Invitation", back_populates="owner_device", cascade="all, delete-orphan")


class SafeZone(Base):
    __tablename__ = "safezones"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    device = relationship("Device", back_populates="safezones")


class LocationEvent(Base):
    __tablename__ = "location_events"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="locations")


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="alerts")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="contacts")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, nullable=False)
    environment = Column(String, nullable=False, default="sandbox")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    device = relationship("Device", back_populates="tokens")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    owner_device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    subscriber_device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner_device = relationship(
        "Device",
        foreign_keys=[owner_device_id],
        back_populates="subscriptions_owned",
    )
    subscriber_device = relationship(
        "Device",
        foreign_keys=[subscriber_device_id],
        back_populates="subscriptions_subscribed",
    )


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        UniqueConstraint("owner_device_id", name="uq_invitation_owner_device"),
        UniqueConstraint("code", name="uq_invitation_code"),
    )

    id = Column(Integer, primary_key=True)
    owner_device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner_device = relationship("Device", back_populates="invitations")
