from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from reconcile.importer import import_a, import_b, import_locations, read_csv


class Command(BaseCommand):
    help = "Import locations.csv, system_a.csv, and system_b.csv"

    def handle(self, *args, **options):
        data_dir = Path(__file__).resolve().parents[3] / "data"
        locations_path = data_dir / "locations.csv"
        a_path = data_dir / "system_a.csv"
        b_path = data_dir / "system_b.csv"

        missing = [str(path) for path in (locations_path, a_path, b_path) if not path.exists()]
        if missing:
            raise CommandError("Missing CSV files: " + ", ".join(missing))

        locations_read = len(read_csv(locations_path))
        a_read = len(read_csv(a_path))
        b_read = len(read_csv(b_path))
        locations_count = import_locations(locations_path)
        a_saved = import_a(a_path)
        b_saved = import_b(b_path)

        if (
            locations_count != locations_read
            or a_saved != a_read
            or b_saved != b_read
        ):
            raise CommandError(
                "Import count mismatch: "
                f"locations={locations_read}/{locations_count}, "
                f"A={a_read}/{a_saved}, B={b_read}/{b_saved}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Locations: {locations_read} read, {locations_count} saved; "
                f"A: {a_read} read, {a_saved} saved; "
                f"B: {b_read} read, {b_saved} saved"
            )
        )
