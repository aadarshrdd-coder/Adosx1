from django.db import models


class Location(models.Model):
    location_id = models.CharField(max_length=50, primary_key=True)
    org_id = models.CharField(max_length=50, db_index=True)

    def __str__(self):
        return f"{self.location_id} ({self.org_id})"


class SystemARecord(models.Model):
    record_id = models.CharField(max_length=50, primary_key=True)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="a_records", null=True, blank=True
    )
    location_id_raw = models.CharField(max_length=50, null=True, blank=True)
    event_date = models.CharField(max_length=50, null=True, blank=True)
    base_value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    adjustment = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    actor_id = models.CharField(max_length=50, null=True, blank=True)
    raw_row = models.JSONField(default=dict)


class SystemBEntry(models.Model):
    entry_id = models.CharField(max_length=50, primary_key=True)
    record_ref = models.CharField(max_length=50, null=True, blank=True)
    cleaned_ref = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="b_entries", null=True, blank=True
    )
    location_id_raw = models.CharField(max_length=50, null=True, blank=True)
    recorded_on = models.CharField(max_length=50, null=True, blank=True)
    value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    raw_row = models.JSONField(default=dict)


class CSVSourceRow(models.Model):
    source = models.CharField(max_length=20)
    row_number = models.PositiveIntegerField()
    raw_data = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "row_number"],
                name="unique_source_row",
            )
        ]

# Create your models here.
