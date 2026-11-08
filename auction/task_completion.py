"""Verified task fulfillment after auction closure.

An auction being closed means bidding has finished, not that the work is done.
Only an owner can confirm completed work, and only if a winner exists.
"""
from django.db import models


class TaskCompletion(models.Model):
    auction = models.OneToOneField(
        "auction.Auction", on_delete=models.PROTECT, related_name="completion",
    )
    confirmed_by = models.ForeignKey(
        "auction.User", on_delete=models.PROTECT, related_name="confirmed_tasks",
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]
