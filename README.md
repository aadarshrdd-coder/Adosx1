# DealerOS Reconciliation

A Django and React app that imports System A and System B CSV ledgers, reconciles them with Decimal values, and exposes tenant-filtered disagreements.

The importer saves every CSV source row in `CSVSourceRow`, including rows that cannot become comparable records. A blank or repeated record/entry identifier gets a stable import identifier while the original row stays intact in `raw_row`. Unparseable amounts remain null and are logged; unmapped locations are preserved but cannot be assigned to an org or shown in the tenant API.

## Run locally

Requires Python 3.11+ and Node.js 20.19+.

```powershell
cd Adosx
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
New-Item -ItemType Directory -Force backend\data
# Copy locations.csv, system_a.csv, and system_b.csv into backend\data
cd backend
python manage.py migrate
python manage.py import_data
python manage.py runserver
```

Place `locations.csv`, `system_a.csv`, and `system_b.csv` in `backend/data/`. In another terminal at the project root:

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`.

## Tests

```powershell
cd Adosx\backend
pytest
```

## API

`GET /api/disagreements/?org=ORG-A&reason=VALUE_MISMATCH&sort=-value`

The `org` parameter is required for tenant-safe use. Locations from `locations.csv` determine ownership; the frontend never hides cross-tenant rows locally.

## Deliberately omitted

Authentication, pagination, Docker, server-side authorization beyond the org parameter, and custom CSS beyond a plain table.

## How I worked with the agent

I used Copilot in VS Code to scaffold the Django and React app, implement CSV import and comparison, and build the tenant-filtered API and table. I reviewed the importer and comparison rules, corrected the package-file issue exposed during migration, and added tests for reconciliation, dirty-row retention, idempotent imports, and tenant boundaries. I ran the Django checks and tests and built the frontend; I could not verify the real reconciliation counts because the three CSV files were not present in the workspace.

## Three answers

### a. One thing the AI agent got wrong

The initial implementation was missing the project migration and management package structure, so Django could not discover the importer until the package files were corrected. Running migrations and imports immediately exposed the issue.

### b. Least confident

I am least confident about the voided-record rule and the cross-org handling until the real three CSV files are loaded, because those rows require business and tenant decisions against actual values.

### c. What I would fix with a second day

I would validate the application against the actual 120/121-row CSVs, add import logging and raw bad-cell counters, and add API tests for every cross-org and reason combination.
