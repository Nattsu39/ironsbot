from datetime import datetime, timedelta, timezone

TZ_CN = timezone(timedelta(hours=8))


def now(tz: timezone | None = None) -> datetime:
    if tz is None:
        return datetime.now(timezone.utc).astimezone()
    return datetime.now(tz=tz)


__all__ = [
    "TZ_CN",
    "now",
]
