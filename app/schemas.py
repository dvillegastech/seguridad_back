from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class DeviceRegisterRequest(BaseSchema):
    device_id: str = Field(alias="deviceId")
    platform: str = "ios"


class DeviceTokenRequest(BaseSchema):
    device_id: str = Field(alias="deviceId")
    token: str
    environment: str


class SafeZoneRequest(BaseSchema):
    device_id: str = Field(alias="deviceId")
    name: str
    latitude: float
    longitude: float
    radius_meters: float = Field(alias="radiusMeters")
    is_active: bool = Field(alias="isActive")


class LocationUpdateRequest(BaseSchema):
    device_id: str = Field(alias="deviceId")
    latitude: float
    longitude: float
    accuracy: float
    timestamp: datetime


class AlertEventRequest(BaseSchema):
    device_id: str = Field(alias="deviceId")
    type: str
    timestamp: datetime
    latitude: float | None = None
    longitude: float | None = None


class ContactRequest(BaseSchema):
    device_id: str = Field(alias="deviceId")
    name: str
    phone: str


class SubscriptionRequest(BaseSchema):
    owner_device_id: str = Field(alias="ownerDeviceId")
    subscriber_device_id: str = Field(alias="subscriberDeviceId")


class InvitationRequest(BaseSchema):
    owner_device_id: str = Field(alias="ownerDeviceId")


class InvitationResponse(BaseSchema):
    code: str
    expires_at: datetime = Field(alias="expiresAt")


class SubscriptionConfirmRequest(BaseSchema):
    code: str
    subscriber_device_id: str = Field(alias="subscriberDeviceId")


class SubscriptionConfirmResponse(BaseSchema):
    owner_device_id: str = Field(alias="ownerDeviceId")


class LocationResponse(BaseModel):
    latitude: float
    longitude: float
    accuracy: float
    timestamp: datetime
