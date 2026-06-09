import uuid

from django.contrib.auth.models import User
from django.db import models


class BlockReason(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    description = models.TextField()
    hard_block = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "block_reasons"


class QueuePriority(models.IntegerChoices):
    FIRST = 1
    SECOND = 2
    THIRD = 3
    FOURTH = 4


class TicketStatus(models.TextChoices):
    MODERATED = "MODERATED"
    APPROVED = "APPROVED"
    IN_REVIEW = "IN_REVIEW"
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    HARD_BLOCKED = "HARD_BLOCKED"

class TicketKind(models.TextChoices):
    CREATE = "CREATE"
    EDIT = "EDIT"


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_id = models.UUIDField()
    seller_id = models.UUIDField()
    json_before = models.JSONField(null=True, blank=True)
    json_after = models.JSONField()
    status = models.TextField(choices=TicketStatus.choices)
    kind = models.TextField(choices=TicketKind.choices)
    queue_priority = models.IntegerField(
        choices=QueuePriority.choices, null=True, blank=True, default=1
    )
    blocking_reasons = models.ManyToManyField(BlockReason)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    claim_expires_at = models.DateTimeField(null=True, blank=True)
    assigned_moderator = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True, blank=True)
    decision_comment = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "tickets"
        ordering = ["queue_priority", "updated_at"]

class ModerActions(models.TextChoices):
    CREATED = "CREATED"
    CLAIMED = "CLAIMED"
    RELEASED = "RELEASED"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    HARD_BLOCKED = "HARD_BLOCKED"
    AUTO_RETURNED = "AUTO_RETURNED"

class Decision(models.Model):
    id = models.UUIDField(primary_key=True, default=True, editable=True)
    action = models.TextField(choices=ModerActions)
    comment = models.TextField()
    at = models.DateTimeField(auto_now_add=True)
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="decisions")
    moderation_ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="history")

    class Meta:
        db_table = "decisions"
        ordering = ["-at"]

class FieldReportSeverity(models.TextChoices):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class FieldReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    field_path = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.TextField(choices=FieldReportSeverity)

    class Meta:
        db_table = "field_reports"

class EventsIdempotencyKeys(models.Model):
    idempotency_key = models.UUIDField(editable=False)
