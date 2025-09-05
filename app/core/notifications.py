import os
import logging
import asyncio
from typing import Iterable, List, Union
import firebase_admin
from firebase_admin import credentials, messaging
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)

SERVICE_ACCOUNT_FILE = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE", "service-account.json")

notification_rates = defaultdict(list)
MAX_NOTIFICATIONS_PER_MINUTE = 1

def _ensure_firebase_initialized() -> bool:
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
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


def _check_rate_limit(user_id: int) -> bool:
    now = datetime.now()
    user_notifications = notification_rates[user_id]
    
    user_notifications[:] = [ts for ts in user_notifications if now - ts < timedelta(minutes=1)]
    
    # Check if user has exceeded limit
    if len(user_notifications) >= MAX_NOTIFICATIONS_PER_MINUTE:
        logger.warning(f"Rate limit exceeded for user {user_id}")
        return False
    
    # Add current notification timestamp
    user_notifications.append(now)
    return True


def _verify_digital_signature(signature_data: str, expected_hash: str = None) -> dict:
    try:
        signature_hash = hashlib.sha256(signature_data.encode()).hexdigest()
        
        # If expected hash provided, compare
        if expected_hash:
            is_valid = signature_hash == expected_hash
        else:
            is_valid = True  # Assume valid if no expected hash provided
        
        return {
            "signature_hash": signature_hash,
            "is_valid": is_valid,
            "verified_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error verifying digital signature: {e}")
        return {
            "signature_hash": None,
            "is_valid": False,
            "error": str(e),
            "verified_at": datetime.now().isoformat()
        }


async def send_firebase_notification(
    tokens: Union[str, Iterable[str]],
    title: str,
    body: str,
    user_id: int = None,
) -> dict:
    if user_id and not _check_rate_limit(user_id):
        return {
            "sent": 0,
            "rate_limited": True,
            "message": "Rate limit exceeded - max 1 notification per minute per user"
        }
    
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
        response = await asyncio.to_thread(messaging.send_multicast, message, dry_run=False)
        logger.info("FCM v1 sent: success=%s failure=%s", response.success_count, response.failure_count)
        return {"sent": response.success_count, "failed": response.failure_count}
    except Exception:
        logger.exception("FCM v1 send failed")
        return {"sent": 0}


async def create_system_notification(
    db,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "system"
) -> dict:
    """Create system notification with rate limiting"""
    try:
        from app.models.notification import Notification
        
        # Check rate limit
        if not _check_rate_limit(user_id):
            return {
                "success": False, 
                "error": "Rate limit exceeded - max 1 notification per minute per user"
            }
        
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type
        )
        db.add(notification)
        await db.flush()  
        logger.info(f"System notification created for user {user_id}: {title}")
        return {"success": True, "notification_id": notification.id}
    except Exception as e:
        logger.exception(f"Failed to create system notification: {e}")
        return {"success": False, "error": str(e)}


async def verify_and_store_signature(
    db,
    user_id: int,
    signature_data: str,
    evaluator_id: int = None,
    expected_hash: str = None
) -> dict:
    try:
        from app.models.admin_log import AdminLog
        
        # Verify signature
        verification_result = _verify_digital_signature(signature_data, expected_hash)
        
        # Log verification result
        db.add(AdminLog(
            type="signature_verification",
            message=f"Digital signature verification: {'Valid' if verification_result['is_valid'] else 'Invalid'}",
            actor_user_id=user_id,
            meta={
                "signature_hash": verification_result["signature_hash"],
                "is_valid": verification_result["is_valid"],
                "evaluation_id": evaluator_id,
                "verified_at": verification_result["verified_at"]
            }
        ))
        await db.commit()
        
        logger.info(f"Signature verification completed for user {user_id}: {verification_result['is_valid']}")
        return verification_result
        
    except Exception as e:
        logger.exception(f"Failed to verify and store signature: {e}")
        return {
            "signature_hash": None,
            "is_valid": False,
            "error": str(e),
            "verified_at": datetime.now().isoformat()
        }


