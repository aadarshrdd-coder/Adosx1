import csv
import logging
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction

from .compare import clean_ref
from .models import CSVSourceRow, Location, SystemARecord, SystemBEntry

logger = logging.getLogger(__name__)
NUMBER_PATTERN = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)\Z")


def text(row, name):
    value = row.get(name)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def decimal_value(row, name):
    raw_value = text(row, name)
    if raw_value is None:
        return None
    normalized = raw_value.replace(",", "")
    try:
        if not NUMBER_PATTERN.fullmatch(normalized):
            raise InvalidOperation
        value = Decimal(normalized)
        if (
            not value.is_finite()
            or value.as_tuple().exponent < -2
            or abs(value) >= Decimal("10000000000000000")
        ):
            raise InvalidOperation
        return value
    except InvalidOperation:
        logger.warning("Could not parse %s value %r; preserving the source row", name, raw_value)
        return None


def raw_row(row):
    return {
        str(key) if key is not None else "_extra_columns": value
        for key, value in row.items()
    }


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def save_source_row(source, row_number, row):
    CSVSourceRow.objects.update_or_create(
        source=source,
        row_number=row_number,
        defaults={"raw_data": raw_row(row)},
    )


def location_lookup():
    return {location.location_id: location for location in Location.objects.all()}


@transaction.atomic
def import_locations(path):
    count = 0
    seen_location_ids = set()
    for row_number, row in enumerate(read_csv(path), start=2):
        save_source_row("locations", row_number, row)
        location_id = text(row, "location_id")
        org_id = text(row, "org_id")
        if not location_id or not org_id:
            logger.warning(
                "Location CSV row %d has no location_id or org_id; preserving the source row",
                row_number,
            )
        else:
            if location_id in seen_location_ids:
                logger.warning(
                    "Location CSV row %d repeats location_id %r; the last mapping is used",
                    row_number,
                    location_id,
                )
            Location.objects.update_or_create(
                location_id=location_id,
                defaults={"org_id": org_id},
            )
            seen_location_ids.add(location_id)
        count += 1
    return count


@transaction.atomic
def import_a(path):
    count = 0
    seen_record_ids = set()
    known_locations = location_lookup()
    for row_number, row in enumerate(read_csv(path), start=2):
        save_source_row("system_a", row_number, row)
        record_id = text(row, "record_id")
        location_id = text(row, "location_id")
        location = known_locations.get(location_id)
        if not record_id:
            logger.warning(
                "System A row %d has no record_id; assigning a stable import identifier",
                row_number,
            )
            record_id = f"__A_ROW_{row_number}"
        elif record_id in seen_record_ids:
            logger.warning(
                "System A row %d repeats record_id %r; preserving it with an import identifier",
                row_number,
                record_id,
            )
            record_id = f"__A_ROW_{row_number}"
        if location_id and not location:
            logger.warning(
                "System A row %d references unmapped location %r",
                row_number,
                location_id,
            )
        SystemARecord.objects.update_or_create(
            record_id=record_id,
            defaults={
                "location": location,
                "location_id_raw": location_id,
                "event_date": text(row, "event_date"),
                "base_value": decimal_value(row, "base_value"),
                "adjustment": decimal_value(row, "adjustment"),
                "total_value": decimal_value(row, "total_value"),
                "state": text(row, "state"),
                "actor_id": text(row, "actor_id"),
                "raw_row": raw_row(row),
            },
        )
        seen_record_ids.add(text(row, "record_id") or f"__A_ROW_{row_number}")
        count += 1
    return count


@transaction.atomic
def import_b(path):
    count = 0
    seen_entry_ids = set()
    known_locations = location_lookup()
    for row_number, row in enumerate(read_csv(path), start=2):
        save_source_row("system_b", row_number, row)
        entry_id = text(row, "entry_id")
        record_ref = text(row, "record_ref")
        location_id = text(row, "location_id")
        location = known_locations.get(location_id)
        if not entry_id:
            logger.warning(
                "System B row %d has no entry_id; assigning a stable import identifier",
                row_number,
            )
            entry_id = f"__B_ROW_{row_number}"
        elif entry_id in seen_entry_ids:
            logger.warning(
                "System B row %d repeats entry_id %r; preserving it with an import identifier",
                row_number,
                entry_id,
            )
            entry_id = f"__B_ROW_{row_number}"
        if location_id and not location:
            logger.warning(
                "System B row %d references unmapped location %r",
                row_number,
                location_id,
            )
        SystemBEntry.objects.update_or_create(
            entry_id=entry_id,
            defaults={
                "record_ref": record_ref,
                "cleaned_ref": clean_ref(record_ref),
                "location": location,
                "location_id_raw": location_id,
                "recorded_on": text(row, "recorded_on"),
                "value": decimal_value(row, "value"),
                "raw_row": raw_row(row),
            },
        )
        seen_entry_ids.add(text(row, "entry_id") or f"__B_ROW_{row_number}")
        count += 1
    return count
