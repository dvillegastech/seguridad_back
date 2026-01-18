from datetime import datetime, timedelta
import secrets
from sqlalchemy.orm import Session

from . import models, schemas


def get_device_by_device_id(db: Session, device_id: str) -> models.Device | None:
    return db.query(models.Device).filter(models.Device.device_id == device_id).first()


def get_device_by_id(db: Session, device_id: int) -> models.Device | None:
    return db.get(models.Device, device_id)


def get_or_create_device(db: Session, device_id: str, platform: str) -> models.Device:
    device = get_device_by_device_id(db, device_id)
    if device:
        device.platform = platform
        device.last_seen_at = datetime.utcnow()
        db.commit()
        db.refresh(device)
        return device

    device = models.Device(device_id=device_id, platform=platform)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def upsert_safezone(db: Session, payload: schemas.SafeZoneRequest) -> models.SafeZone:
    device = get_or_create_device(db, payload.device_id, "ios")
    zone = (
        db.query(models.SafeZone)
        .filter(models.SafeZone.device_id == device.id, models.SafeZone.name == payload.name)
        .first()
    )
    if zone is None:
        zone = models.SafeZone(device_id=device.id, name=payload.name)
        db.add(zone)

    zone.latitude = payload.latitude
    zone.longitude = payload.longitude
    zone.radius_meters = payload.radius_meters
    zone.is_active = payload.is_active
    zone.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(zone)
    return zone


def create_location(db: Session, payload: schemas.LocationUpdateRequest) -> models.LocationEvent:
    device = get_or_create_device(db, payload.device_id, "ios")
    event = models.LocationEvent(
        device_id=device.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        timestamp=payload.timestamp,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def create_alert(db: Session, payload: schemas.AlertEventRequest) -> models.AlertEvent:
    device = get_or_create_device(db, payload.device_id, "ios")
    alert = models.AlertEvent(
        device_id=device.id,
        type=payload.type,
        timestamp=payload.timestamp,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def upsert_contact(db: Session, payload: schemas.ContactRequest) -> models.Contact:
    device = get_or_create_device(db, payload.device_id, "ios")
    contact = (
        db.query(models.Contact)
        .filter(models.Contact.device_id == device.id, models.Contact.phone == payload.phone)
        .first()
    )
    if contact is None:
        contact = models.Contact(device_id=device.id, name=payload.name, phone=payload.phone)
        db.add(contact)
    else:
        contact.name = payload.name

    db.commit()
    db.refresh(contact)
    return contact


def upsert_device_token(db: Session, payload: schemas.DeviceTokenRequest) -> models.DeviceToken:
    device = get_or_create_device(db, payload.device_id, "ios")
    token = db.query(models.DeviceToken).filter(models.DeviceToken.token == payload.token).first()
    if token is None:
        token = models.DeviceToken(
            device_id=device.id,
            token=payload.token,
            environment=payload.environment,
        )
        db.add(token)
    else:
        token.device_id = device.id
        token.environment = payload.environment
        token.last_seen_at = datetime.utcnow()

    db.commit()
    db.refresh(token)
    return token


def create_subscription(db: Session, payload: schemas.SubscriptionRequest) -> models.Subscription:
    owner = get_or_create_device(db, payload.owner_device_id, "ios")
    subscriber = get_or_create_device(db, payload.subscriber_device_id, "ios")
    existing = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.owner_device_id == owner.id,
            models.Subscription.subscriber_device_id == subscriber.id,
        )
        .first()
    )
    if existing:
        return existing

    subscription = models.Subscription(
        owner_device_id=owner.id,
        subscriber_device_id=subscriber.id,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_subscriber_tokens(db: Session, owner_device_id: str) -> list[models.DeviceToken]:
    owner = get_device_by_device_id(db, owner_device_id)
    if owner is None:
        return []
    return (
        db.query(models.DeviceToken)
        .join(models.Subscription, models.Subscription.subscriber_device_id == models.DeviceToken.device_id)
        .filter(models.Subscription.owner_device_id == owner.id)
        .all()
    )


def get_invitation_by_owner(db: Session, owner_device_id: str) -> models.Invitation | None:
    owner = get_device_by_device_id(db, owner_device_id)
    if owner is None:
        return None
    return (
        db.query(models.Invitation)
        .filter(models.Invitation.owner_device_id == owner.id)
        .first()
    )


def create_or_rotate_invitation(
    db: Session,
    payload: schemas.InvitationRequest,
    ttl_days: int = 7,
) -> models.Invitation:
    owner = get_or_create_device(db, payload.owner_device_id, "ios")
    existing = (
        db.query(models.Invitation)
        .filter(models.Invitation.owner_device_id == owner.id)
        .first()
    )
    expires_at = datetime.utcnow() + timedelta(days=ttl_days)
    code = _generate_unique_code(db)

    if existing:
        existing.code = code
        existing.expires_at = expires_at
        db.commit()
        db.refresh(existing)
        return existing

    invitation = models.Invitation(
        owner_device_id=owner.id,
        code=code,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def confirm_subscription_with_code(
    db: Session,
    payload: schemas.SubscriptionConfirmRequest,
) -> str | None:
    invitation = (
        db.query(models.Invitation)
        .filter(models.Invitation.code == payload.code)
        .first()
    )
    if invitation is None:
        return None
    if invitation.expires_at < datetime.utcnow():
        return None

    subscriber = get_or_create_device(db, payload.subscriber_device_id, "ios")
    existing = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.owner_device_id == invitation.owner_device_id,
            models.Subscription.subscriber_device_id == subscriber.id,
        )
        .first()
    )
    if existing:
        owner = get_device_by_id(db, invitation.owner_device_id)
        return owner.device_id if owner else None

    subscription = models.Subscription(
        owner_device_id=invitation.owner_device_id,
        subscriber_device_id=subscriber.id,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    owner = get_device_by_id(db, invitation.owner_device_id)
    return owner.device_id if owner else None


def _generate_unique_code(db: Session, length: int = 6) -> str:
    for _ in range(10):
        code = "".join(secrets.choice("0123456789") for _ in range(length))
        exists = db.query(models.Invitation).filter(models.Invitation.code == code).first()
        if not exists:
            return code
    return secrets.token_hex(3)


def get_latest_location(db: Session, device_id: str) -> models.LocationEvent | None:
    device = get_device_by_device_id(db, device_id)
    if device is None:
        return None
    return (
        db.query(models.LocationEvent)
        .filter(models.LocationEvent.device_id == device.id)
        .order_by(models.LocationEvent.timestamp.desc())
        .first()
    )


def get_location_history(db: Session, device_id: str, limit: int) -> list[models.LocationEvent]:
    device = get_device_by_device_id(db, device_id)
    if device is None:
        return []
    return (
        db.query(models.LocationEvent)
        .filter(models.LocationEvent.device_id == device.id)
        .order_by(models.LocationEvent.timestamp.desc())
        .limit(limit)
        .all()
    )
