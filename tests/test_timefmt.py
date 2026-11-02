import datetime

import pytest

from engine import timefmt


def test_stamp_matches_the_documented_shape():
    stamp = timefmt.stamp("UTC")

    assert len(stamp) == 17
    assert stamp[4] == stamp[7] == "-"
    assert stamp[10] == "-"
    datetime.datetime.strptime(stamp, timefmt.STAMP_FORMAT)


def test_local_and_utc_resolve_without_a_zone_database():
    assert timefmt.resolve_timezone("local") is not None
    assert timefmt.resolve_timezone("") is not None
    assert timefmt.resolve_timezone("UTC") == datetime.timezone.utc


def test_fixed_offset_resolves_to_its_own_clock():
    eastern = timefmt.resolve_timezone("-05:00")

    assert eastern.utcoffset(None) == datetime.timedelta(hours=-5)
    assert timefmt.resolve_timezone("+05:30").utcoffset(None) == datetime.timedelta(hours=5, minutes=30)


def test_iana_name_resolves_to_a_zone():
    zone = timefmt.resolve_timezone("America/New_York")

    assert zone is not None
    assert zone.utcoffset(datetime.datetime(2026, 1, 15)) == datetime.timedelta(hours=-5)
    assert zone.utcoffset(datetime.datetime(2026, 7, 15)) == datetime.timedelta(hours=-4)


@pytest.mark.parametrize("name", ["Mars/Olympus", "-25:00", "+10:75"])
def test_unknown_zone_raises_a_readable_error(name):
    with pytest.raises(ValueError) as excinfo:
        timefmt.resolve_timezone(name)

    assert "timezone" in str(excinfo.value).lower() or "offset" in str(excinfo.value)


def test_normalize_stamp_keeps_the_stamp_form():
    assert timefmt.normalize_stamp("2026-10-27-235510") == "2026-10-27-235510"


@pytest.mark.parametrize(
    "value",
    ["2026-10-27T23:55:10", "2026-10-27T23:55:10-04:00", "2026-10-27T23:55:10Z"],
)
def test_normalize_stamp_accepts_iso_8601(value):
    assert timefmt.normalize_stamp(value) == "2026-10-27-235510"


def test_normalize_stamp_passes_empty_values_through():
    assert timefmt.normalize_stamp(None) is None
    assert timefmt.normalize_stamp("   ") is None


@pytest.mark.parametrize("value", ["yesterday", "2026-13-45", "23:55"])
def test_normalize_stamp_rejects_other_text(value):
    with pytest.raises(ValueError) as excinfo:
        timefmt.normalize_stamp(value)

    assert "YYYY-MM-DD-HHMMSS" in str(excinfo.value)
