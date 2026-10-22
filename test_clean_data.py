import pandas as pd
import pytest
from clean_data import clean

MONTH = "2025-01"


def make_trip(**changes):
    """One good trip, with any column changed as asked."""
    trip = {
        "tpep_pickup_datetime": pd.Timestamp("2025-01-10 08:00"),
        "tpep_dropoff_datetime": pd.Timestamp("2025-01-10 08:20"),
        "passenger_count": 1.0,
        "trip_distance": 3.0,
        "fare_amount": 15.0,
        "total_amount": 20.0,
    }
    trip.update(changes)
    return trip


def run(*trips):
    return clean(pd.DataFrame(list(trips)), MONTH)


def test_good_trip_is_kept():
    kept, rejected = run(make_trip())
    assert len(kept) == 1
    assert len(rejected) == 0


@pytest.mark.parametrize("changes, expected_reason", [
    ({"tpep_pickup_datetime": pd.Timestamp("2025-02-05 08:00"),
      "tpep_dropoff_datetime": pd.Timestamp("2025-02-05 08:20")}, "pickup outside the month"),
    ({"tpep_dropoff_datetime": pd.Timestamp("2025-01-10 07:50")}, "trip ends before or when it starts"),
    ({"tpep_dropoff_datetime": pd.Timestamp("2025-01-11 09:00")}, "trip longer than 24 hours"),
    ({"trip_distance": 150.0}, "distance over 100 miles"),
    ({"trip_distance": 0.0}, "distance zero or negative"),
    ({"fare_amount": -5.0}, "fare zero or negative"),
    ({"total_amount": 0.0}, "total zero or negative"),
])
def test_bad_trip_is_rejected_with_reason(changes, expected_reason):
    kept, rejected = run(make_trip(**changes))
    assert len(kept) == 0
    assert rejected["reject_reason"].iloc[0] == expected_reason


def test_missing_passenger_count_is_kept_and_flagged():
    kept, rejected = run(make_trip(passenger_count=float("nan")))
    assert len(kept) == 1
    assert bool(kept["missing_passenger_count"].iloc[0]) is True


def test_zero_passenger_count_is_kept_and_flagged():
    kept, rejected = run(make_trip(passenger_count=0.0))
    assert len(kept) == 1
    assert bool(kept["passenger_count_zero"].iloc[0]) is True


def test_row_counts_add_up():
    trips = [make_trip(), make_trip(trip_distance=0.0), make_trip(fare_amount=-1.0), make_trip()]
    kept, rejected = run(*trips)
    assert len(kept) + len(rejected) == len(trips)


def test_trip_breaking_several_rules_is_counted_once():
    kept, rejected = run(make_trip(trip_distance=0.0, fare_amount=0.0, total_amount=0.0))
    assert len(rejected) == 1
    assert rejected["reject_reason"].iloc[0] == "distance zero or negative"


def test_very_high_fare_on_short_trip_is_rejected():
    kept, rejected = run(make_trip(trip_distance=0.1, fare_amount=900.0, total_amount=901.0))
    assert len(kept) == 0
    assert rejected["reject_reason"].iloc[0] == "fare over $200 on a trip under 10 miles"


def test_high_fare_on_long_trip_is_kept():
    kept, rejected = run(make_trip(trip_distance=90.0, fare_amount=600.0, total_amount=620.0))
    assert len(kept) == 1
    assert bool(kept["fare_high_for_distance"].iloc[0]) is False


def test_moderately_high_fare_on_short_trip_is_kept_and_flagged():
    kept, rejected = run(make_trip(trip_distance=3.0, fare_amount=150.0, total_amount=160.0))
    assert len(kept) == 1
    assert bool(kept["fare_high_for_distance"].iloc[0]) is True
