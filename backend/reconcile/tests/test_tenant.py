import pytest
from django.test import Client

from reconcile.models import Location, SystemARecord, SystemBEntry


@pytest.mark.django_db
def test_org_a_api_cannot_return_org_b_location_or_record():
    a_location = Location.objects.create(location_id="LOC-101", org_id="ORG-A")
    b_location = Location.objects.create(location_id="LOC-201", org_id="ORG-B")
    record = SystemARecord.objects.create(
        record_id="REC-A",
        location=a_location,
        location_id_raw="LOC-101",
        event_date="2026-03-01",
        total_value="100",
    )
    SystemBEntry.objects.create(
        entry_id="E-B",
        record_ref="REC-A",
        cleaned_ref="REC-A",
        location=b_location,
        location_id_raw="LOC-201",
        recorded_on="2026-03-02",
        value="100",
    )

    response = Client().get("/api/disagreements/", {"org": "ORG-A"})
    result = response.json()
    assert {row["reason"] for row in result} == {"LOCATION_MISMATCH", "DATE_MISMATCH"}
    assert all(row["location"] == "LOC-101" for row in result)
    assert all(row["b_value"] is None for row in result)
    assert "LOC-201" not in response.content.decode()
    assert "REC-B" not in response.content.decode()


@pytest.mark.django_db
def test_org_b_can_return_its_own_orphan_only():
    b_location = Location.objects.create(location_id="LOC-201", org_id="ORG-B")
    SystemBEntry.objects.create(
        entry_id="E-B",
        record_ref="REC-999",
        cleaned_ref="REC-999",
        location=b_location,
        location_id_raw="LOC-201",
        recorded_on="2026-03-01",
        value="100",
    )

    response = Client().get("/api/disagreements/", {"org": "ORG-B"})
    text = response.content.decode()
    assert "REC-999" in text
    assert "LOC-201" in text


@pytest.mark.django_db
def test_org_b_cannot_see_a_record_matched_to_org_a():
    a_location = Location.objects.create(location_id="LOC-101", org_id="ORG-A")
    b_location = Location.objects.create(location_id="LOC-201", org_id="ORG-B")
    SystemARecord.objects.create(
        record_id="REC-A",
        location=a_location,
        location_id_raw="LOC-101",
        event_date="2026-03-01",
        total_value="100",
    )
    SystemBEntry.objects.create(
        entry_id="E-B",
        record_ref="REC-A",
        cleaned_ref="REC-A",
        location=b_location,
        location_id_raw="LOC-201",
        recorded_on="2026-03-01",
        value="90",
    )

    response = Client().get("/api/disagreements/", {"org": "ORG-B"})
    assert response.json() == []


@pytest.mark.django_db
def test_org_parameter_is_required():
    response = Client().get("/api/disagreements/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_api_sorts_numeric_values_and_keeps_blanks_last_in_both_directions():
    location = Location.objects.create(location_id="LOC-101", org_id="ORG-A")
    for record_id, b_value in [("REC-1", "20"), ("REC-2", "100"), ("REC-3", "")]:
        SystemARecord.objects.create(
            record_id=record_id,
            location=location,
            location_id_raw="LOC-101",
            event_date="2026-03-01",
            total_value="50",
        )
        SystemBEntry.objects.create(
            entry_id=f"E-{record_id}",
            record_ref=record_id,
            cleaned_ref=record_id,
            location=location,
            location_id_raw="LOC-101",
            recorded_on="2026-03-01",
            value=b_value or None,
        )

    client = Client()
    ascending = client.get("/api/disagreements/", {"org": "ORG-A", "reason": "VALUE_MISMATCH"})
    descending = client.get(
        "/api/disagreements/",
        {"org": "ORG-A", "reason": "VALUE_MISMATCH", "sort": "-value"},
    )
    assert [row["b_value"] for row in ascending.json()] == ["20.00", "100.00", None]
    assert [row["b_value"] for row in descending.json()] == ["100.00", "20.00", None]
