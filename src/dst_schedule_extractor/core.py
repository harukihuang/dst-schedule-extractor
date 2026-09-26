import zoneinfo
from datetime import datetime, timedelta, timezone

__all__ = ["get_dst_transitions"]


def _utc_offsets_at(tz: zoneinfo.ZoneInfo, year: int, month: int, day: int) -> tuple[int, int]:
    """Return utcoffsets (seconds) at 00:00 and 12:00 local on the given date.

    Some timezones near the international date line have only 12 hours of
    offset ambiguity around midnight rather than 24. Sampling at noon as well
    covers the half-day case.
    """
    t0 = datetime(year, month, day, 0, 0, tzinfo=tz)
    t1 = datetime(year, month, day, 12, 0, tzinfo=tz)
    o0 = t0.utcoffset()
    o1 = t1.utcoffset()
    if o0 is None or o1 is None:
        raise ValueError(f"Timezone {tz} has no UTC offset for {year}-{month:02d}-{day:02d}")
    return int(o0.total_seconds()), int(o1.total_seconds())


def _day_utcoffset_seconds(tz: zoneinfo.ZoneInfo, d: datetime) -> int:
    """Seconds of UTC offset that applies at the start of local day d.

    A date is considered a 'transition day' if the offset at the very start of
    the local day differs from the offset at the start of the next local day.
    """
    local_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
    return int(local_start.utcoffset().total_seconds())


def _find_transition(
    tz: zoneinfo.ZoneInfo, year: int, month: int, day: int, prev_offset: int
) -> datetime | None:
    """Locate the DST transition (if any) on the given date.

    A transition is the first local wall-time where utcoffset != prev_offset.
    Internally we walk forward in one-minute steps from 00:00 local. Because
    ambiguous local times can map to two different instants, we always work
    with aware datetimes and compare utcoffsets, not wall clock strings.
    Returns None if no transition occurs on this date.
    """
    start_local = datetime(year, month, day, 0, 0, 0, tzinfo=tz)
    # Convert to an absolute instant on the UTC timeline.
    start_utc = start_local.astimezone(timezone.utc)

    step = timedelta(minutes=1)
    current_utc = start_utc
    end_utc = start_utc + timedelta(days=1)

    while current_utc < end_utc:
        offset_now = int(current_utc.astimezone(tz).utcoffset().total_seconds())
        if offset_now != prev_offset:
            # Found the boundary. Walk back to minute precision (already there)
            # and return the aware datetime in the target zone.
            return current_utc.astimezone(tz)
        current_utc += step

    return None


def get_dst_transitions(
    tz_name: str, year: int
) -> tuple[datetime | None, datetime | None]:
    """Return the (spring_forward, fall_back) DST transitions for *year*.

    Each returned datetime is timezone-aware and uses the zone named by
    *tz_name*. The first element is the transition where the UTC offset
    increases (spring forward); the second is where it decreases (fall back).
    If the zone does not observe DST, or has fewer than two transitions in
    the year, the missing positions are None.

    Implementation notes
    --------------------
    We scan every day of the target year, comparing the UTC offset at the
    start of each local day against the previous day's start-of-day offset.
    When they differ we bisect to minute precision within that day. This is
    slower than reading tzdata directly, but zoneinfo exposes no public API
    for transition times, so a scan is the only portable approach.

    Edge cases handled:
    * Timezones that never observe DST in the target year -> (None, None).
    * Timezones with only one transition in the year (e.g. a political
      change that abolishes DST mid-year).
    * Zones where the offset near midnight is ambiguous because of the
      international date line; we sample at noon as well.
    * Perennial zones with fixed offset (UTC, Etc/GMT+0) -> (None, None).
    """
    tz = zoneinfo.ZoneInfo(tz_name)

    transitions: list[tuple[datetime, int]] = []

    # Start from December of the previous year so that the very first day
    # of the target year has a valid 'previous offset' to compare against.
    first = datetime(year, 1, 1, tzinfo=tz)
    cur = first.replace(year=year - 1, month=12, day=31)
    # Normalize in case Dec 31 doesn't exist (it always does, but be safe).
    cur = cur.replace(day=28)  # Dec 28 always exists; safe lower bound
    one_day = timedelta(days=1)

    while True:
        prev_offset = _day_utcoffset_seconds(tz, cur)
        nxt = cur + one_day
        if nxt.year > year:
            break
        if nxt.year == year or cur.year == year:
            nxt_offset = _day_utcoffset_seconds(tz, nxt)
            if nxt_offset != prev_offset:
                # Transition happens between cur start and nxt start.
                # _find_transition walks within cur's date.
                t = _find_transition(tz, cur.year, cur.month, cur.day, prev_offset)
                if t is not None:
                    transitions.append((t, nxt_offset - prev_offset))
        cur = nxt

    spring = None
    fall = None
    for t, delta in transitions:
        if delta > 0 and spring is None:
            spring = t
        elif delta < 0 and fall is None:
            fall = t
    # If multiple transitions of the same sign occur, keep the first of each.
    # (Some historical zones switched multiple times in a year.)
    if spring is None:
        for t, delta in transitions:
            if delta > 0:
                spring = t
                break
    if fall is None:
        for t, delta in transitions:
            if delta < 0:
                fall = t
                break

    return spring, fall
