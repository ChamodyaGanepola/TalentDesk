"""Sri Lanka timezone helpers with Windows-safe fallback."""

from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo

    try:
        COLOMBO = ZoneInfo("Asia/Colombo")
    except Exception:
        # Windows often needs the `tzdata` package for IANA zones.
        COLOMBO = timezone(timedelta(hours=5, minutes=30), name="Asia/Colombo")
except Exception:
    COLOMBO = timezone(timedelta(hours=5, minutes=30), name="Asia/Colombo")


def now_sri_lanka() -> datetime:
    return datetime.now(COLOMBO)


def to_sri_lanka(dt: datetime | None) -> datetime:
    if dt is None:
        return now_sri_lanka()

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(COLOMBO)


def now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
