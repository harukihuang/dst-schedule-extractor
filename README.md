# DST Schedule Extractor

Finds the precise dates of daylight saving time transitions for a timezone, using only the Python standard library.

```python
from dst_schedule_extractor import get_dst_transitions

spring, fall = get_dst_transitions("America/New_York", 2024)
print(spring)  # 2024-03-10 07:00:00-05:00 (the instant DST begins, in zone local time)
print(fall)    # 2024-11-03 06:00:00-04:00 (the instant DST ends, in zone local time)
```

## Why this exists

Working code that needs to display or schedule around DST boundaries usually hardcodes second-Sunday-of-March style rules. That works until a jurisdiction changes its rules, at which point the hardcoded logic silently produces wrong answers. This library reads the system's tzdata through `zoneinfo` and scans the target year to find the actual transitions the installed database reports. The trade-off is speed: a full-year scan with minute resolution is far slower than a lookup table, but it is correct against whatever tzdata is installed and requires no third-party packages.

## Edge cases

* Timezones that do not observe DST in the given year return `(None, None)` — including fixed-offset zones like `UTC` and `Etc/GMT+5`.
* The returned datetimes are timezone-aware and expressed in the *target* zone's local frame. The offset shown is the offset that applies immediately *after* the transition (e.g. spring-forward in New York shows `-04:00`, not the pre-transition `-05:00`).
* If a zone has more than one transition of the same sign in a year (historical political changes), the library keeps the first of each sign. This is a deliberate, single interpretation rather than attempting to rank historical transitions.
* The scan starts from December of the previous year so that January 1 always has a valid prior offset to compare against.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

