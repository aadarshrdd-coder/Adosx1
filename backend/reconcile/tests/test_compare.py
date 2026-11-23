from decimal import Decimal

from reconcile.compare import clean_ref, compare


def a_record(total="100.00", location="LOC-101", date="2026-03-01"):
    return {"total": Decimal(total), "location": location, "date": date}


def b_entry(entry_id="E1", ref="REC-1", value="100.00", location="LOC-101", date="2026-03-01"):
    return {"entry_id": entry_id, "ref": ref, "value": value, "location": location, "date": date}


def test_missing_in_b():
    assert compare({"REC-1": a_record()}, []) == [
        {"reason": "MISSING_IN_B", "record_id": "REC-1", "entry_id": None}
    ]


def test_orphan_in_b():
    result = compare({}, [b_entry(ref="REC-999")])
    assert result[0]["reason"] == "ORPHAN_IN_B"
    assert result[0]["record_id"] == "REC-999"


def test_orphan_without_reference_has_a_stable_display_identifier():
    result = compare({}, [b_entry(entry_id="E-ORPHAN", ref=None)])
    assert result[0]["record_id"] == "UNMATCHED:E-ORPHAN"


def test_duplicate_in_b():
    result = compare(
        {"REC-1": a_record(total="100.00")},
        [b_entry("E1", "REC-1", "50.00"), b_entry("E2", "REC-1", "40.00")],
    )
    assert any(row["reason"] == "DUPLICATE_IN_B" for row in result)


def test_value_mismatch():
    assert any(
        row["reason"] == "VALUE_MISMATCH"
        for row in compare({"REC-1": a_record()}, [b_entry(value="90.00")])
    )


def test_blank_value_is_not_zero():
    assert any(
        row["reason"] == "VALUE_MISMATCH"
        for row in compare({"REC-1": a_record()}, [b_entry(value="")])
    )


def test_split_entries_that_add_to_total_are_not_flagged():
    assert compare(
        {"REC-1": a_record(total="100.00")},
        [b_entry("E1", "REC-1", "40.00"), b_entry("E2", "REC-1", "60.00")],
    ) == []


def test_messy_references_match_clean_record():
    assert clean_ref("rec1034") == "REC-1034"
    assert clean_ref("REC - 1070") == "REC-1070"
    assert clean_ref("1112") == "REC-1112"
    assert compare(
        {"REC-1034": a_record(location="LOC-101")},
        [b_entry(ref="rec1034", location="LOC-101")],
    ) == []


def test_clean_row_has_no_disagreement():
    assert compare({"REC-1": a_record()}, [b_entry()]) == []


def test_location_mismatch():
    assert any(
        row["reason"] == "LOCATION_MISMATCH"
        for row in compare({"REC-1": a_record(location="LOC-101")}, [b_entry(location="LOC-201")])
    )


def test_date_mismatch():
    assert any(
        row["reason"] == "DATE_MISMATCH"
        for row in compare({"REC-1": a_record(date="2026-03-01")}, [b_entry(date="2026-03-02")])
    )


def test_voided_record_is_not_reported_as_missing_or_mismatched():
    record = a_record(total="100.00")
    record["state"] = "VOIDED"
    assert compare({"REC-1": record}, []) == []
