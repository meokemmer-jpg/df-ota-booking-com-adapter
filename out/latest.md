# df-ota-booking-com-adapter — Output [CRUX-MK]
*Autonom aktiviert 2026-06-05T15:49:04.819549+00:00 | ollama-local/qwen2.5:14b-instruct*

# df-ota-booking-com-adapter [CRUX-MK]

## Zusammenfassung

Der Dark-Factory `df-ota-booking-com-adapter` ist eine integrierte Lösung f
für die Verbindung mit Booking.coms XML-API und EAN-Rate-API. Sie ermöglich
ermöglicht die Synchronisierung von Verfügbarkeit, Tarifen sowie Buchungsbe
Buchungsbenachrichtigungen. Dieses Dokument enthält Konfigurationen, Module
Module und Tests, um sicherzustellen, dass der Adapter fehlerfrei funktioni
funktioniert.

## Zweck

- **XML-API:** Abfragen nach Verfügbarkeit und Annehmen von Buchungen.
- **EAN-Rate-API:** Aktualisierung von Tarifen.
- **Webhook:** Empfangen von Buchungsbenachrichtigungen mit HMAC-SHA256 Ver
Verifikation.
- **18%-Kommission-Tracker:** Registrierung der Kommission pro Booking.

## Vendor-API-Pattern

- **XML-API (Inventory + Bookings)**
- **EAN-Rate-API (Rates Push)**
- **Webhook (Notifications mit HMAC-SHA256 Verification)**
- **Hotelier-Account-Login (hotelier_id + api_key)**

### Default-Modus: Sandbox
Um den Real-Modus zu aktivieren:
- `DF_OTA_BOOKING_COM_REAL_ENABLED=true`
- `BOOKING_COM_HOTELIER_ID` und `BOOKING_COM_API_KEY` eingetragen.
- `DF_OTA_BOOKING_COM_PHRONESIS_TICKET`

## Module

### src/booking_com_adapter.py
- XMLAPIConnector, EAN-Rate-API und 18%-Kommission-Tracker.

### src/booking_com_auth.py
- Muster für den Login des Hotelier-Accounts (Hotelier-ID und API-Schlüssel
API-Schlüssel).

### src/booking_com_webhook.py
- Receiver für Buchungsbenachrichtigungen sowie HMAC-SHA256 Verifikation.

### src/commission_tracker.py
- Registrierung der pro-Buchung erzielten Kommissionen und Aggregatberichte
Aggregatberichte.

### src/adapter_orchestrator.py
- Eintrittspunkt des LaunchAgents.

### src/audit_logger.py
- HMAC-SHA256-versiegelte Audit-Einträge (JSONL anhängbar).

## Tests

`tests/test_booking_com_adapter.py`
- 18+ Tests für Adapter, Authentifizierung, Webhook, Tracker, Orchestrator 
und AuditLogger.

```bash
cd df-ota-booking-com-adapter
PYTHONPATH=. python -m pytest tests/ -v
```

## Ausführung über LaunchAgent

```bash
cp scripts/com.kemmer.df-ota-booking-com-adapter.plist ~/Library/LaunchAgen
~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.kemmer.df-ota-booking-com-adapter
~/Library/LaunchAgents/com.kemmer.df-ota-booking-com-adapter.plist
```
LaunchAgent: `RunAtLoad=true` und `StartInterval=7200` (2 Stunden).

## Compliance

### K11-K16 Compliance

- **K11:** Kaskaden-Haftung durch try/except + LC4 idempotent.
- **K12:** Herkunft via gefrorener Dataclass und Quellverfolgung.
- **K13:** PAV (Pauschale, Anpassbarkeit, Vertrauenswürdigkeit) durch env_t
env_tag und vendor_api anchor.
- **K14:** Überschreibung via single_command + martin_review wöchentlich.
- **K15:** Entropie ~700 LOC mit rho-Justifikation 40k EUR/Jahr.
- **K16:** Concurrent-Spawn-Mutex über mkdir-lock und pgrep.

### LC1-LC5 Compliance

- **LC1:** 3 Degradation-Modi (vollständig, deaktiviert ohne Real-API, Stan
Standalone-Mock).
- **LC2:** Direct-Mode-Capability 0.5 (Mock-Daten ohne Real-API).
- **LC3:** Circuit-Breaker (Timeout 30s, 3 Fehlschläge, Halboffene-Phase 30
300s).
- **LC4:** Fehlerisolierung über externen Zustand und idempotente Operation
Operationen.
- **LC5:** Standalone-Health-Check.

Diese Dark-Factory dient als primäres Output-Artefakt für die Integration m
mit Booking.com und bietet eine robuste Lösung zur Rate-Synchronisierung, B
Buchungsbenachrichtigung und Kommissionsverfolgung.