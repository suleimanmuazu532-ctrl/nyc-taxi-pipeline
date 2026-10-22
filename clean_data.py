"""Clean one month of NYC yellow taxi trips.

Rejected trips are saved with the reason, so nothing disappears silently.
"""
import argparse
import pandas as pd


def find_rejection_reasons(df, month):
    """Return a Series with the first broken rule for each trip ('' = keep)."""
    start = pd.Timestamp(month + "-01")
    end = start + pd.offsets.MonthBegin(1)
    pickup = df["tpep_pickup_datetime"]
    minutes = (df["tpep_dropoff_datetime"] - pickup).dt.total_seconds() / 60

    rules = [
        ("pickup outside the month", (pickup < start) | (pickup >= end)),
        ("trip ends before or when it starts", minutes <= 0),
        ("trip longer than 24 hours", minutes > 24 * 60),
        ("distance over 100 miles", df["trip_distance"] > 100),
        ("distance zero or negative", df["trip_distance"] <= 0),
        ("fare over $200 on a trip under 10 miles", (df["fare_amount"] > 200) & (df["trip_distance"] < 10)),
        ("fare zero or negative", df["fare_amount"] <= 0),
        ("total zero or negative", df["total_amount"] <= 0),
    ]

    reason = pd.Series("", index=df.index)
    for name, bad in rules:
        reason = reason.mask((reason == "") & bad, name)
    return reason


def clean(df, month):
    """Split trips into kept and rejected, and check the row counts add up."""
    reason = find_rejection_reasons(df, month)

    kept = df[reason == ""].copy()
    kept["missing_passenger_count"] = kept["passenger_count"].isna()
    kept["passenger_count_zero"] = kept["passenger_count"] == 0
    kept["fare_high_for_distance"] = (kept["fare_amount"] > 100) & (kept["trip_distance"] < 10)

    rejected = df[reason != ""].copy()
    rejected["reject_reason"] = reason[reason != ""]

    if len(kept) + len(rejected) != len(df):
        raise ValueError("Row counts do not add up")
    return kept, rejected


def main():
    parser = argparse.ArgumentParser(description="Clean one month of taxi trips")
    parser.add_argument("--input", default="data/yellow_tripdata_2025-01.parquet")
    parser.add_argument("--month", default="2025-01")
    args = parser.parse_args()

    df = pd.read_parquet(args.input)
    kept, rejected = clean(df, args.month)

    kept.to_parquet(f"data/clean_{args.month}.parquet", index=False)
    rejected.to_parquet(f"data/rejected_{args.month}.parquet", index=False)

    print("Trips in:", len(df))
    print("Kept:", len(kept))
    print("Rejected:", len(rejected), f"({len(rejected) / len(df) * 100:.1f}%)")
    print()
    print(rejected["reject_reason"].value_counts().to_string())
    print()
    print("Kept but flagged, missing passenger count:", int(kept["missing_passenger_count"].sum()))
    print("Kept but flagged, passenger count zero:", int(kept["passenger_count_zero"].sum()))
    print("Kept but flagged, fare over $100 on a trip under 10 miles:", int(kept["fare_high_for_distance"].sum()))
    print("Row counts add up:", len(kept) + len(rejected) == len(df))


if __name__ == "__main__":
    main()
