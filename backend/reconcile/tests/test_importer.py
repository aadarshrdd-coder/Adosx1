import csv

import pytest

from reconcile.importer import import_a, import_b, import_locations
from reconcile.models import CSVSourceRow, Location, SystemARecord, SystemBEntry


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.django_db
def test_import_preserves_rows_with_blank_ids_and_bad_values(tmp_path):
    locations_path = tmp_path / "locations.csv"
    a_path = tmp_path / "system_a.csv"
    b_path = tmp_path / "system_b.csv"
    write_csv(locations_path, ["location_id", "org_id"], [
        {"location_id": "LOC-1", "org_id": "ORG-A"},
    ])
    write_csv(a_path, [
        "record_id", "location_id", "event_date", "base_value",
        "adjustment", "total_value", "state", "actor_id",
    ], [
        {
            "record_id": "REC-1", "location_id": "LOC-1", "event_date": "2026-03-01",
            "base_value": "not-a-number", "adjustment": "0", "total_value": "",
            "state": "CONFIRMED", "actor_id": "",
        },
        {
            "record_id": "", "location_id": "LOC-1", "event_date": "2026-03-02",
            "base_value": "10", "adjustment": "0", "total_value": "10",
            "state": "CONFIRMED", "actor_id": "",
        },
        {
            "record_id": "REC-1", "location_id": "LOC-1", "event_date": "2026-03-03",
            "base_value": "20", "adjustment": "0", "total_value": "20",
            "state": "CONFIRMED", "actor_id": "",
        },
    ])
    write_csv(b_path, [
        "entry_id", "record_ref", "location_id", "recorded_on", "value",
    ], [
        {
            "entry_id": "E1", "record_ref": "rec1034", "location_id": "LOC-1",
            "recorded_on": "2026-03-01", "value": "1,25,400.00",
        },
        {
            "entry_id": "", "record_ref": "rec1035", "location_id": "LOC-1",
            "recorded_on": "2026-03-02", "value": "",
        },
        {
            "entry_id": "E1", "record_ref": "rec1034", "location_id": "LOC-1",
            "recorded_on": "2026-03-03", "value": "100.00",
        },
    ])

    assert import_locations(locations_path) == 1
    assert import_a(a_path) == 3
    assert import_b(b_path) == 3

    a_record = SystemARecord.objects.get(record_id="REC-1")
    b_entry = SystemBEntry.objects.get(entry_id="E1")
    assert a_record.base_value is None
    assert a_record.raw_row["base_value"] == "not-a-number"
    assert a_record.actor_id is None
    assert b_entry.value == 125400
    assert b_entry.raw_row["value"] == "1,25,400.00"
    assert CSVSourceRow.objects.get(source="system_a", row_number=3).raw_data["record_id"] == ""
    assert CSVSourceRow.objects.get(source="system_b", row_number=3).raw_data["entry_id"] == ""
    assert SystemARecord.objects.filter(record_id="__A_ROW_3").exists()
    assert SystemBEntry.objects.filter(entry_id="__B_ROW_3").exists()
    assert SystemARecord.objects.filter(record_id="__A_ROW_4").exists()
    assert SystemBEntry.objects.filter(entry_id="__B_ROW_4").exists()

    assert import_locations(locations_path) == 1
    assert import_a(a_path) == 3
    assert import_b(b_path) == 3
    assert Location.objects.count() == 1
    assert SystemARecord.objects.count() == 3
    assert SystemBEntry.objects.count() == 3
    assert CSVSourceRow.objects.count() == 7


@pytest.mark.django_db
def test_unmapped_location_does_not_drop_imported_record(tmp_path):
    a_path = tmp_path / "system_a.csv"
    write_csv(a_path, ["record_id", "location_id"], [
        {"record_id": "REC-1", "location_id": "UNKNOWN-LOC"},
    ])

    assert import_a(a_path) == 1
    record = SystemARecord.objects.get(record_id="REC-1")
    assert record.location is None
    assert record.location_id_raw == "UNKNOWN-LOC"
