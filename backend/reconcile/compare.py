import re
from decimal import Decimal, InvalidOperation


def clean_ref(value):
    if value is None:
        return None
    text = str(value).strip()
    compact = re.sub(r"[\s_-]+", "", text).upper()
    if compact.startswith("REC"):
        suffix = re.sub(r"\D", "", compact)
        if suffix:
            return f"REC-{suffix}"
    if compact and compact.isdigit():
        return f"REC-{compact}"
    return text.upper() or None


def clean_decimal(value):
    if value is None or value == "":
        return None
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def compare(a_rows, b_rows):
    by_ref = {}
    for entry in b_rows:
        ref = clean_ref(entry["ref"])
        by_ref.setdefault(ref, []).append(entry)

    disagreements = []
    for ref, entries in by_ref.items():
        if ref not in a_rows:
            for entry in entries:
                disagreements.append({
                    "reason": "ORPHAN_IN_B",
                    "record_id": ref or f"UNMATCHED:{entry['entry_id']}",
                    "entry_id": entry["entry_id"],
                })

    for record_id, a in a_rows.items():
        if str(a.get("state", "")).strip().upper() == "VOIDED":
            continue
        entries = by_ref.get(record_id, [])
        if not entries:
            disagreements.append({
                "reason": "MISSING_IN_B",
                "record_id": record_id,
                "entry_id": None,
            })
            continue

        a_value = clean_decimal(a.get("total"))
        values = [clean_decimal(entry.get("value")) for entry in entries]
        if len(entries) > 1:
            if a_value is None or any(value is None for value in values):
                disagreements.append({
                    "reason": "VALUE_MISMATCH",
                    "record_id": record_id,
                    "entry_id": ", ".join(str(entry["entry_id"]) for entry in entries if entry["entry_id"]),
                })
            elif sum(values, Decimal("0")) != a_value:
                disagreements.append({
                    "reason": "DUPLICATE_IN_B",
                    "record_id": record_id,
                    "entry_id": ", ".join(str(entry["entry_id"]) for entry in entries if entry["entry_id"]),
                })
            continue

        entry = entries[0]
        if a_value is None or values[0] is None or values[0] != a_value:
            disagreements.append({
                "reason": "VALUE_MISMATCH",
                "record_id": record_id,
                "entry_id": entry["entry_id"],
            })
        if entry["location"] != a.get("location"):
            disagreements.append({
                "reason": "LOCATION_MISMATCH",
                "record_id": record_id,
                "entry_id": entry["entry_id"],
            })
        if entry["date"] != a.get("date"):
            disagreements.append({
                "reason": "DATE_MISMATCH",
                "record_id": record_id,
                "entry_id": entry["entry_id"],
            })

    return disagreements
