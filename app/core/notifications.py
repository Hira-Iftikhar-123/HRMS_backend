import os
import logging
import asyncio
from typing import Iterable, List, Union
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

SERVICE_ACCOUNT_FILE = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE", "service-account.json")


def _ensure_firebase_initialized() -> bool:
    """Initialize Firebase Admin SDK once per process. Returns True if ready."""
    try:
        # If already initialized, this will succeed
        firebase_admin.get_app()
        return True
    except ValueError:
        # Not initialized yet
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            logger.warning("Firebase service account file not found: %s", SERVICE_ACCOUNT_FILE)
            return False
        try:
            cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized")
            return True
        except Exception:
            logger.exception("Failed to initialize Firebase Admin SDK")
            return False


async def send_firebase_notification(
    tokens: Union[str, Iterable[str]],
    title: str,
    body: str,
) -> dict:
    """
    Send a Firebase Cloud Messaging push notification using the Admin SDK
    (HTTP v1 under the hood). Accepts a single token or a list of tokens.
    """
    if isinstance(tokens, str):
        token_list: List[str] = [tokens]
    else:
        token_list = list(tokens)

    if not token_list:
        logger.info("No FCM tokens provided; skipping notification")
        return {"sent": 0}

    if not _ensure_firebase_initialized():
        return {"sent": 0}

    notification = messaging.Notification(title=title, body=body)
    message = messaging.MulticastMessage(notification=notification, tokens=token_list)

    try:
        # messaging.send_multicast is synchronous; run it in a worker thread
        response = await asyncio.to_thread(messaging.send_multicast, message, dry_run=False)
        logger.info("FCM v1 sent: success=%s failure=%s", response.success_count, response.failure_count)
        return {"sent": response.success_count, "failed": response.failure_count}
    except Exception:
        logger.exception("FCM v1 send failed")
        return {"sent": 0}


