"""df-ota-booking-com-adapter [CRUX-MK].

Welle-37 HeyLou-Mosaic-Adapter fuer Booking.com OTA (EU-Marktfuehrer).

LAZY-IMPORT-PATTERN: Module werden bei Bedarf importiert.
"""

from __future__ import annotations

__version__ = "0.1.0-SKELETON"
__df_id__ = "df-ota-booking-com-adapter"
__welle__ = "welle-37"


def get_connector():
    from src.booking_com_adapter import BookingComConnector
    return BookingComConnector


def get_auth_manager():
    from src.booking_com_auth import BookingComAuthManager
    return BookingComAuthManager


def get_webhook_handler():
    from src.booking_com_webhook import BookingComWebhookHandler
    return BookingComWebhookHandler


def get_commission_tracker():
    from src.commission_tracker import CommissionTracker
    return CommissionTracker


def get_orchestrator():
    from src.adapter_orchestrator import BookingComAdapterOrchestrator
    return BookingComAdapterOrchestrator


def get_audit_logger():
    from src.audit_logger import AuditLogger
    return AuditLogger


__all__ = [
    "__version__",
    "__df_id__",
    "__welle__",
    "get_connector",
    "get_auth_manager",
    "get_webhook_handler",
    "get_commission_tracker",
    "get_orchestrator",
    "get_audit_logger",
]
