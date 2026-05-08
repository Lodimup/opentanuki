"""Abstract base models shared across the scheduler app."""
import uuid

from django.db import models


class BaseUUID(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid7,
        help_text="Unique identifier for this record",
    )

    class Meta:
        abstract = True


class BaseAutoDate(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this record was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this record was last updated")

    class Meta:
        abstract = True
