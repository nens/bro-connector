import datetime

import pandas as pd
import polars as pl
from tools.signals import (
    _filter_gmn_rows,
    _validate_gmn_columns,
    convert_str_to_datetime,
    determine_separator,
    normalize_sample,
)
from tools.utils import _deduplicate_measurements


def test_normalize_sample_and_determine_separator():
    sample = b"code;date\nA;2024-01-01\n"

    assert normalize_sample(sample).startswith("code;date")
    assert determine_separator(sample) == ";"


def test_convert_str_to_datetime_supports_date_and_invalid_values():
    assert convert_str_to_datetime("01/02/2024") == datetime.datetime(2024, 2, 1)
    assert convert_str_to_datetime(datetime.date(2024, 2, 1)) == datetime.datetime(
        2024, 2, 1
    )
    assert convert_str_to_datetime("not-a-date") is None


def test_validate_gmn_columns_reports_missing_and_unexpected_columns():
    frame = pl.DataFrame(
        {
            "measuringPointCode": ["MP-1"],
            "gmwBroId": ["GMW000000000001"],
            "unexpected": ["value"],
        }
    )

    columns, messages = _validate_gmn_columns(frame)

    assert columns == []
    assert any("Missende kolommen" in message for message in messages)
    assert any("Onverwachte kolommen" in message for message in messages)


def test_filter_gmn_rows_keeps_first_date_and_logs_removed_rows():
    frame = pl.DataFrame(
        {
            "measuringPointCode": ["MP-1", "MP-2", "MP-3", "MP-4"],
            "gmwBroId": ["GMW-1", "GMW-2", "GMW-3", "GMW-4"],
            "tubeNumber": [1, 2, 3, 4],
            "date": ["2024-01-01", "2024-01-01", "2024-02-01", "not-a-date"],
        }
    )

    rows, messages, validated = _filter_gmn_rows(
        frame, ["measuringPointCode", "gmwBroId", "tubeNumber", "date"]
    )

    assert validated is False
    assert len(rows) == 2
    assert rows[0]["measuringPointCode"] == "MP-1"
    assert any("dubbele datum" in message for message in messages)
    assert any("ongeldige datum" in message for message in messages)


def test_deduplicate_measurements_keeps_first_value_and_logs_duplicate():
    measurements = pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 00:00", "2024-01-02 00:00"],
                utc=True,
            ),
            "value": [1.0, 2.0, 3.0],
        }
    )

    cleaned, report = _deduplicate_measurements(measurements, "time", "value")

    assert cleaned["value"].tolist() == [1.0, 3.0]
    assert "Rij 3 verwijderd" in report
    assert "waarde '2.0'" in report
    assert "Eerste waarde op rij 2 behouden" in report
