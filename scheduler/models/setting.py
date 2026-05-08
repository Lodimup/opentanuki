from django.db import models

from ._base import BaseAutoDate, BaseUUID


class Setting(BaseUUID, BaseAutoDate):
    """Singleton-style key/value store for app config (OAuth token, etc)."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key: str, value: str) -> "Setting":
        obj, _ = cls.objects.update_or_create(key=key, defaults={"value": value})
        return obj
