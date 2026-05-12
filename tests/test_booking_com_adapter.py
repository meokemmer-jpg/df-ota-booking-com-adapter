"""Tests fuer Booking.com OTA-Adapter [CRUX-MK]. Welle-37."""

from __future__ import annotations
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.booking_com_adapter import BookingComConnector, AdapterResponse, OTAAdapter
from src.booking_com_auth import BookingComAuthManager, BookingComCredentials
from src.booking_com_webhook import BookingComWebhookHandler, WebhookVerificationResult
from src.commission_tracker import CommissionTracker, CommissionRecord
from src.adapter_orchestrator import BookingComAdapterOrchestrator, LoopReport
from src.audit_logger import AuditLogger, AuditEntry


class TestBookingComAdapter:
    def test_sandbox_default(self):
        c = BookingComConnector()
        assert c.sandbox_mode is True
        assert c.adapter_name == "booking-com-ota"
        assert c.COMMISSION_PCT == 0.18

    def test_connect_sandbox(self):
        c = BookingComConnector(sandbox_mode=True)
        assert c.connect({}) is True
        assert c._connected is True

    def test_query_inventory(self):
        c = BookingComConnector(sandbox_mode=True)
        c.connect({})
        inv = c.query_inventory("hildesheim", ("2026-06-01", "2026-06-02"))
        assert len(inv) == 3
        for r in inv:
            assert r["commission_pct"] == 0.18
            assert "rate_eur" in r

    def test_query_inventory_unknown_hotel(self):
        c = BookingComConnector(sandbox_mode=True)
        c.connect({})
        assert c.query_inventory("unknown", ("2026-06-01", "2026-06-02")) == []

    def test_push_rate_sandbox(self):
        c = BookingComConnector(sandbox_mode=True)
        c.connect({})
        assert c.push_rate("hildesheim", "standard", "2026-06-01", 99.0) is True

    def test_push_rate_real_no_phronesis(self, monkeypatch):
        monkeypatch.setenv("DF_OTA_BOOKING_COM_REAL_ENABLED", "true")
        monkeypatch.delenv("DF_OTA_BOOKING_COM_PHRONESIS_TICKET", raising=False)
        c = BookingComConnector(sandbox_mode=False)
        c._connected = True
        assert c.push_rate("hildesheim", "standard", "2026-06-01", 99.0) is False

    def test_pull_bookings(self):
        c = BookingComConnector(sandbox_mode=True)
        c.connect({})
        bookings = c.pull_bookings("hildesheim", "2026-06-01T00:00:00Z")
        assert isinstance(bookings, list)

    def test_get_capabilities(self):
        c = BookingComConnector(sandbox_mode=True)
        caps = c.get_capabilities()
        assert caps["vendor"] == "booking-com"
        assert caps["commission_pct"] == 0.18
        assert caps["feature_flags"]["xml_api"] is True

    def test_implements_ota_adapter(self):
        c = BookingComConnector(sandbox_mode=True)
        assert isinstance(c, OTAAdapter)


class TestBookingComAuth:
    def test_sandbox_credentials(self):
        a = BookingComAuthManager(sandbox_mode=True)
        creds = a.get_credentials("hildesheim")
        assert creds is not None
        assert creds.source == "mock"

    def test_validate_none(self):
        a = BookingComAuthManager(sandbox_mode=True)
        assert a.validate(None) is False

    def test_validate_valid(self):
        a = BookingComAuthManager(sandbox_mode=True)
        creds = a.get_credentials("hildesheim")
        assert a.validate(creds) is True

    def test_real_mode_no_env(self, monkeypatch):
        monkeypatch.setenv("DF_OTA_BOOKING_COM_REAL_ENABLED", "true")
        monkeypatch.delenv("BOOKING_COM_HOTELIER_ID", raising=False)
        monkeypatch.delenv("BOOKING_COM_API_KEY", raising=False)
        a = BookingComAuthManager()
        assert a.get_credentials("hildesheim") is None


class TestBookingComWebhook:
    def test_verify_valid_signature(self):
        h = BookingComWebhookHandler(secret="test-secret", sandbox_mode=True)
        body = b'{"event_type":"booking_created","booking_id":"bkg-123"}'
        import hmac, hashlib
        sig = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        assert h.verify_signature(body, sig) is True

    def test_verify_invalid_signature(self):
        h = BookingComWebhookHandler(secret="test-secret", sandbox_mode=True)
        assert h.verify_signature(b'{"a":1}', "invalid") is False

    def test_replay_protection(self):
        import time
        h = BookingComWebhookHandler(secret="test-secret", sandbox_mode=True)
        old = time.time() - 1000
        assert h.verify_signature(b'{"a":1}', "any", timestamp=old) is False

    def test_handle_webhook_valid(self):
        h = BookingComWebhookHandler(secret="test-secret", sandbox_mode=True)
        body = b'{"event_type":"booking_created","booking_id":"bkg-456"}'
        import hmac, hashlib
        sig = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        result = h.handle_webhook(body, sig)
        assert result.valid is True
        assert result.event_type == "booking_created"
        assert result.booking_id == "bkg-456"


class TestCommissionTracker:
    def test_record_booking(self, tmp_path):
        t = CommissionTracker(storage_dir=str(tmp_path))
        rec = t.record_booking({
            "booking_id": "bkg-1", "hotel_id": "hildesheim", "rate_eur": 100.0,
        })
        assert rec.commission_eur == 18.0
        assert rec.commission_pct == 0.18

    def test_aggregate_period_empty(self, tmp_path):
        t = CommissionTracker(storage_dir=str(tmp_path))
        agg = t.aggregate_period("hildesheim", "monthly")
        assert agg["bookings_count"] == 0

    def test_aggregate_period_with_records(self, tmp_path):
        t = CommissionTracker(storage_dir=str(tmp_path))
        for i in range(3):
            t.record_booking({"booking_id": f"b{i}", "hotel_id": "hildesheim", "rate_eur": 100.0})
        agg = t.aggregate_period("hildesheim", "monthly")
        assert agg["bookings_count"] == 3
        assert agg["total_commission_eur"] == 54.0  # 3 * 18

    def test_export_jsonl(self, tmp_path):
        t = CommissionTracker(storage_dir=str(tmp_path))
        t.record_booking({"booking_id": "x1", "hotel_id": "h1", "rate_eur": 100.0})
        n = t.export_jsonl(str(tmp_path / "export.jsonl"))
        assert n == 1


class TestOrchestrator:
    def test_orchestrator_init(self):
        o = BookingComAdapterOrchestrator()
        assert o.DF_ID == "df-ota-booking-com-adapter"
        assert o.sandbox_mode is True

    def test_orchestrator_run_sandbox(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        o = BookingComAdapterOrchestrator()
        report = o.run()
        assert isinstance(report, LoopReport)
        assert report.df_id == "df-ota-booking-com-adapter"
        assert report.final_status in ("complete", "partial")

    def test_orchestrator_dry_run(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        o = BookingComAdapterOrchestrator()
        report = o.run(dry_run=True)
        assert "sample_query" not in report.phases_passed or report.final_status in ("complete", "partial")

    def test_loop_report_persistence(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        o = BookingComAdapterOrchestrator()
        report = o.run()
        report_dir = tmp_path / "runs" / "loop-reports"
        assert report_dir.exists()


class TestAuditLogger:
    def test_log_audit_entry(self, tmp_path):
        a = AuditLogger(audit_dir=str(tmp_path))
        entry = a.log("test_event", {"key": "value"})
        assert entry.event_type == "test_event"
        assert entry.signature is not None

    def test_verify_signature(self, tmp_path):
        a = AuditLogger(audit_dir=str(tmp_path))
        entry = a.log("test_event", {"key": "value"})
        assert entry.verify_signature() is True

    def test_read_recent(self, tmp_path):
        a = AuditLogger(audit_dir=str(tmp_path))
        a.log("e1", {"i": 1})
        a.log("e2", {"i": 2})
        entries = a.read_recent(limit=10)
        assert len(entries) >= 2

    def test_audit_entry_immutable(self):
        e = AuditEntry(
            event_type="t", df_id="d", timestamp_iso="2026-06-01",
            payload={"a": 1},
        )
        with pytest.raises((AttributeError, Exception)):
            e.event_type = "x"
