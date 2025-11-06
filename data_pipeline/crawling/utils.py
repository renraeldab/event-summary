def timestamp_valid(ts: float | None, start: float | None, end: float | None) -> bool:
    """Return True if `ts` falls within the inclusive range [start, end].

    Parameters:
        ts (float | None): Timestamp to check. If None, considered valid (returns True).
        start (float | None): Lower bound (inclusive). If None, no lower bound.
        end (float | None): Upper bound (inclusive). If None, no upper bound.

    Returns:
        bool: True if `ts` is within the specified bounds, False otherwise.
    """
    if ts is None:
        return True
    if start is not None and ts < start:
        return False
    if end is not None and ts > end:
        return False
    return True
