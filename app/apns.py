import logging
import os
import time

import httpx
import jwt
from sqlalchemy.orm import Session

from . import crud


logger = logging.getLogger("seguridad.apns")


def send_alert_push(db: Session, owner_device_id: str, alert_type: str) -> None:
    tokens = crud.get_subscriber_tokens(db, owner_device_id)
    if not tokens:
        return

    apns_topic = os.getenv("APNS_TOPIC", "")
    team_id = os.getenv("APNS_TEAM_ID", "")
    key_id = os.getenv("APNS_KEY_ID", "")
    auth_key = os.getenv("APNS_AUTH_KEY", "")
    if "\\n" in auth_key:
        auth_key = auth_key.replace("\\n", "\n")

    if not apns_topic or not team_id or not key_id or not auth_key:
        logger.warning("APNs not configured; missing env vars.")
        return

    jwt_token = _create_jwt(team_id=team_id, key_id=key_id, auth_key=auth_key)
    payload = _alert_payload(alert_type)

    with httpx.Client(http2=True, timeout=10.0) as client:
        for token in tokens:
            host = _apns_host(token.environment)
            url = f"{host}/3/device/{token.token}"
            headers = {
                "authorization": f"bearer {jwt_token}",
                "apns-topic": apns_topic,
                "apns-push-type": "alert",
                "apns-priority": "10",
                "apns-expiration": "0",
            }
            response = client.post(url, headers=headers, json=payload)
            if response.status_code >= 300:
                logger.warning(
                    "APNs error %s: %s", response.status_code, response.text
                )


def _create_jwt(team_id: str, key_id: str, auth_key: str) -> str:
    now = int(time.time())
    headers = {"kid": key_id}
    payload = {"iss": team_id, "iat": now}
    return jwt.encode(payload, auth_key, algorithm="ES256", headers=headers)


def _apns_host(environment: str) -> str:
    if environment == "production":
        return "https://api.push.apple.com"
    return "https://api.sandbox.push.apple.com"


def _alert_payload(alert_type: str) -> dict:
    if alert_type == "enter":
        body = "Ingreso a la zona segura."
    else:
        body = "Salida de la zona segura."
    return {
        "aps": {
            "alert": {
                "title": "Seguridad",
                "body": body,
            },
            "sound": "default",
        }
    }
