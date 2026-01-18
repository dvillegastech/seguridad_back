import logging
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from dotenv import load_dotenv

from . import apns, crud, models, schemas
from .db import Base, engine, get_db


load_dotenv()

app = FastAPI(title="Seguridad API")
logger = logging.getLogger("seguridad.api")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/devices/register")
def register_device(payload: schemas.DeviceRegisterRequest, db: Session = Depends(get_db)):
    device = crud.get_or_create_device(db, payload.device_id, payload.platform)
    return {"deviceId": device.device_id}


@app.post("/device-tokens")
def register_device_token(payload: schemas.DeviceTokenRequest, db: Session = Depends(get_db)):
    crud.upsert_device_token(db, payload)
    return {"status": "ok"}


@app.post("/safezones")
def upsert_safezone(payload: schemas.SafeZoneRequest, db: Session = Depends(get_db)):
    crud.upsert_safezone(db, payload)
    return {"status": "ok"}


@app.post("/locations")
def create_location(payload: schemas.LocationUpdateRequest, db: Session = Depends(get_db)):
    crud.create_location(db, payload)
    return {"status": "ok"}


@app.post("/alerts")
def create_alert(payload: schemas.AlertEventRequest, db: Session = Depends(get_db)):
    crud.create_alert(db, payload)
    try:
        apns.send_alert_push(db, payload.device_id, payload.type)
    except Exception as exc:
        logger.warning("APNs push failed: %s", exc)
    return {"status": "ok"}


@app.post("/contacts")
def upsert_contact(payload: schemas.ContactRequest, db: Session = Depends(get_db)):
    crud.upsert_contact(db, payload)
    return {"status": "ok"}


@app.post("/subscriptions")
def create_subscription(payload: schemas.SubscriptionRequest, db: Session = Depends(get_db)):
    crud.create_subscription(db, payload)
    return {"status": "ok"}


@app.post("/invites", response_model=schemas.InvitationResponse)
def create_invitation(payload: schemas.InvitationRequest, db: Session = Depends(get_db)):
    invitation = crud.create_or_rotate_invitation(db, payload)
    return schemas.InvitationResponse(code=invitation.code, expiresAt=invitation.expires_at)


@app.get("/invites/{device_id}", response_model=schemas.InvitationResponse)
def get_invitation(device_id: str, db: Session = Depends(get_db)):
    invitation = crud.get_invitation_by_owner(db, device_id)
    if invitation is None:
        raise HTTPException(status_code=404, detail="No invitation")
    return schemas.InvitationResponse(code=invitation.code, expiresAt=invitation.expires_at)


@app.post("/subscriptions/confirm")
def confirm_subscription(payload: schemas.SubscriptionConfirmRequest, db: Session = Depends(get_db)):
    owner_device_id = crud.confirm_subscription_with_code(db, payload)
    if owner_device_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    return schemas.SubscriptionConfirmResponse(ownerDeviceId=owner_device_id)


@app.get("/locations/latest/{device_id}", response_model=schemas.LocationResponse)
def latest_location(device_id: str, db: Session = Depends(get_db)):
    event = crud.get_latest_location(db, device_id)
    if event is None:
        raise HTTPException(status_code=404, detail="No location data")
    return schemas.LocationResponse(
        latitude=event.latitude,
        longitude=event.longitude,
        accuracy=event.accuracy,
        timestamp=event.timestamp,
    )


@app.get("/locations/history/{device_id}", response_model=list[schemas.LocationResponse])
def location_history(device_id: str, limit: int = 100, db: Session = Depends(get_db)):
    events = crud.get_location_history(db, device_id, limit=limit)
    return [
        schemas.LocationResponse(
            latitude=event.latitude,
            longitude=event.longitude,
            accuracy=event.accuracy,
            timestamp=event.timestamp,
        )
        for event in events
    ]


@app.get("/safezones/{device_id}")
def list_safezones(device_id: str, db: Session = Depends(get_db)):
    device = crud.get_device_by_device_id(db, device_id)
    if device is None:
        return []
    zones = (
        db.query(models.SafeZone)
        .filter(models.SafeZone.device_id == device.id)
        .order_by(models.SafeZone.updated_at.desc())
        .all()
    )
    return [
        {
            "name": zone.name,
            "latitude": zone.latitude,
            "longitude": zone.longitude,
            "radiusMeters": zone.radius_meters,
            "isActive": zone.is_active,
        }
        for zone in zones
    ]


@app.get("/contacts/{device_id}")
def list_contacts(device_id: str, db: Session = Depends(get_db)):
    device = crud.get_device_by_device_id(db, device_id)
    if device is None:
        return []
    contacts = (
        db.query(models.Contact)
        .filter(models.Contact.device_id == device.id)
        .order_by(models.Contact.created_at.desc())
        .all()
    )
    return [
        {"name": contact.name, "phone": contact.phone}
        for contact in contacts
    ]
