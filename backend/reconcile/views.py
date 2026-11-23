from decimal import Decimal

from django.db.models import Q
from django.http import JsonResponse

from .compare import compare
from .models import SystemARecord, SystemBEntry

REASONS = {
    "MISSING_IN_B",
    "ORPHAN_IN_B",
    "DUPLICATE_IN_B",
    "VALUE_MISMATCH",
    "LOCATION_MISMATCH",
    "DATE_MISMATCH",
}


def disagreement_api(request):
    org = (request.GET.get("org") or "").strip()
    if not org:
        return JsonResponse({"error": "The org query parameter is required."}, status=400)

    reason_filter = (request.GET.get("reason") or "").strip()
    if reason_filter and reason_filter not in REASONS:
        return JsonResponse({"error": "Unknown disagreement reason."}, status=400)

    sort = (request.GET.get("sort") or "value").strip()
    if sort not in {"value", "-value"}:
        return JsonResponse({"error": "sort must be value or -value."}, status=400)

    a_records = list(
        SystemARecord.objects
        .filter(location__org_id=org)
        .select_related("location")
        .order_by("record_id")
    )
    a_rows = {}
    a_by_id = {}
    for record in a_records:
        if not record.record_id:
            continue
        a_rows[record.record_id] = {
            "total": record.total_value,
            "location": record.location.location_id,
            "date": record.event_date,
            "state": record.state,
        }
        a_by_id[record.record_id] = record

    own_b_entries = list(
        SystemBEntry.objects
        .filter(location__org_id=org)
        .select_related("location")
        .order_by("entry_id")
    )
    own_refs = {entry.cleaned_ref for entry in own_b_entries if entry.cleaned_ref}
    existing_refs = set(
        SystemARecord.objects
        .filter(record_id__in=own_refs)
        .values_list("record_id", flat=True)
    )
    orphan_ids = [
        entry.pk for entry in own_b_entries
        if not entry.cleaned_ref or entry.cleaned_ref not in existing_refs
    ]

    related_b_entries = list(
        SystemBEntry.objects
        .filter(Q(location__org_id=org) | Q(cleaned_ref__in=a_by_id))
        .filter(Q(cleaned_ref__in=a_by_id) | Q(pk__in=orphan_ids))
        .select_related("location")
        .order_by("entry_id")
    )
    b_rows = [
        {
            "entry_id": entry.entry_id,
            "ref": entry.cleaned_ref,
            "value": entry.value,
            "location": entry.location.location_id if entry.location else None,
            "date": entry.recorded_on,
        }
        for entry in related_b_entries
    ]
    entries_by_ref = {}
    for entry in related_b_entries:
        entries_by_ref.setdefault(entry.cleaned_ref, []).append(entry)

    output = []
    for item in compare(a_rows, b_rows):
        reason = item["reason"]
        if reason_filter and reason != reason_filter:
            continue

        record_id = item["record_id"]
        if reason == "ORPHAN_IN_B":
            entry = next(
                (candidate for candidate in related_b_entries
                 if candidate.entry_id == item["entry_id"]),
                None,
            )
            if entry is None or entry.location is None or entry.location.org_id != org:
                continue
            location = entry.location_id_raw
            a_value = None
            b_value = entry.value
        else:
            record = a_by_id.get(record_id)
            if record is None:
                continue
            location = record.location_id_raw
            a_value = record.total_value
            matched_entries = entries_by_ref.get(record_id, [])
            foreign_entry = any(
                entry.location is None or entry.location.org_id != org
                for entry in matched_entries
            )
            if foreign_entry:
                b_value = None
            elif len(matched_entries) > 1:
                values = [entry.value for entry in matched_entries]
                b_value = sum(values, Decimal("0")) if all(value is not None for value in values) else None
            elif matched_entries:
                b_value = matched_entries[0].value
            else:
                b_value = None

        a_text = format(a_value, "f") if a_value is not None else None
        b_text = format(b_value, "f") if b_value is not None else None
        difference = (
            format(a_value - b_value, "f")
            if a_value is not None and b_value is not None
            else None
        )
        output.append({
            "reason": reason,
            "record_id": record_id,
            "location": location,
            "a_value": a_text,
            "b_value": b_text,
            "difference": difference,
        })

    valued_rows = [row for row in output if row["b_value"] is not None]
    missing_value_rows = [row for row in output if row["b_value"] is None]
    valued_rows.sort(
        key=lambda row: Decimal(row["b_value"]),
        reverse=sort == "-value",
    )
    return JsonResponse(valued_rows + missing_value_rows, safe=False)
