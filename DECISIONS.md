## Decision: compare B value with A total_value
- Rejected: comparing with base_value.
- Why: B represents the final ledger amount, while adjustment is included in total_value.

## Decision: preserve unknown values as null
- Rejected: converting blanks or bad values to zero.
- Why: unknown is not an amount; Decimal parsing logs bad values and raw_row retains the original text.

## Decision: retain malformed source rows separately
- Rejected: skipping rows with a missing ID or unmapped location.
- Why: every source line is stored in CSVSourceRow; comparable rows use a stable import ID when their source ID is blank or repeated.

## Decision: treat split entries as valid
- Rejected: flagging every record with multiple B entries.
- Why: multiple entries are allowed only when their values sum exactly to A's total.

## Decision: treat two entries as duplicates when they do not sum to total
- Rejected: treating any repeated amount as a split.
- Why: a duplicate or unrelated pair is a disagreement unless the parts add to the A total exactly.

## Decision: count date and location differences
- Rejected: ignoring them.
- Why: they are independent evidence that the two systems describe the event differently.

## Decision: exclude VOIDED A records from reconciliation
- Rejected: reporting their missing B entries or comparing their B values.
- Why: a voided event is treated as outside the active ledger; confirm this assumption with the business owner.

## Decision: hide cross-org B details
- Rejected: displaying B location and value beside an A-owned row.
- Why: ORG-A must not receive details owned by ORG-B. The row is shown under the A side, but foreign location and value are blank.
