from celery import shared_task
from src.models.moderation import Ticket, TicketStatus
from django.utils import timezone
import logging

@shared_task
def update_expired_tickets():
    tickets = Ticket.objects.filter(status=TicketStatus.IN_REVIEW, claim_expires_at__lt=timezone.now())
    for ticket in tickets:
        ticket.status = TicketStatus.PENDING
        ticket.save()
    logging.info("expired tickets updated")