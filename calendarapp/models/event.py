from datetime import datetime
from django.db import models
from django.urls import reverse

from calendarapp.models import EventAbstract
from accounts.models import User


class EventManager(models.Manager):
    """ Event manager """

    def get_all_events(self, user):
        events = Event.objects.filter(user=user, is_active=True, is_deleted=False)
        return events

    def get_running_events(self, user):
        running_events = Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            end_time__gte=datetime.now().date(),
            start_time__lte = datetime.now().date()
        ).order_by("start_time")
        return running_events
    
    def get_completed_events(self, user):
        completed_events = Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            end_time__lt=datetime.now().date(),
        )
        return completed_events
    
    def get_upcoming_events(self, user):
        upcoming_events = Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            start_time__gt=datetime.now().date(),
        )
        return upcoming_events


class Event(EventAbstract):
    """ Event model """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=200)
    # replaced description with more structured fields
    head = models.CharField(max_length=150, blank=True, null=True)
    IMPORTANCE_CHOICES = (
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
    )
    importance = models.CharField(max_length=10, choices=IMPORTANCE_CHOICES, default="normal")
    location = models.CharField(max_length=200, blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    objects = EventManager()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("calendarapp:event-detail", args=(self.id,))

    @property
    def get_html_url(self):
        url = reverse("calendarapp:event-detail", args=(self.id,))
        return f'<a href="{url}"> {self.title} </a>'

    def conflicting_events(self):
        """Return queryset of events for same user that overlap this event's time range (excluding self)."""
        return Event.objects.filter(
            user=self.user,
            is_active=True,
            is_deleted=False,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(id=self.id)

    @property
    def has_conflict(self):
        return self.conflicting_events().exists()
