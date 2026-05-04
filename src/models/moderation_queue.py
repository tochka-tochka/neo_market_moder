import uuid
from django.db import models

class Queue(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    product = models.UUIDField()
    date = models.DateField()

    class Meta:
        db_table = "queue"
        ordering =["-date"]

class BlockReason(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    reason = models.TextField()

    class Meta:
        db_table = "block_reasons"