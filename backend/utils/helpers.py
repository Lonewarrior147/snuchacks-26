from datetime import datetime, timezone


def time_ago(dt: datetime) -> str:
    """Convert a datetime to a human-readable 'X ago' string."""
    if dt is None:
        return "unknown"

    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    return f"{months}mo ago"


def format_currency(amount: float) -> str:
    """Format amount as Indian Rupee string."""
    return f"₹{amount:,.2f}"
