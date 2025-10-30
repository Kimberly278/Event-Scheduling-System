from django.forms import ModelForm, DateInput
from calendarapp.models import Event, EventMember
from django import forms
from django.core.exceptions import ValidationError


class EventForm(ModelForm):
    class Meta:
        model = Event
        fields = ["title", "head", "importance", "location", "start_time", "end_time"]
        # datetime-local is a HTML5 input type
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter event title"}
            ),
            "head": forms.TextInput(attrs={"class": "form-control", "placeholder": "Head of event / short summary"}),
            "importance": forms.Select(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "Where the event is held"}),
            "start_time": DateInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_time": DateInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
        }
        exclude = ["user"]

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        # input_formats to parse HTML5 datetime-local input to datetime field
        self.fields["start_time"].input_formats = ("%Y-%m-%dT%H:%M",)
        self.fields["end_time"].input_formats = ("%Y-%m-%dT%H:%M",)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and start >= end:
            raise ValidationError("End time must be after start time.")
        return cleaned


class AddMemberForm(forms.ModelForm):
    class Meta:
        model = EventMember
        fields = ["user"]
