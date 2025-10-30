# cal/views.py

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.views import generic
from django.utils.safestring import mark_safe
from datetime import timedelta, datetime, date
import calendar
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from calendarapp.models import EventMember, Event
from calendarapp.utils import Calendar
from calendarapp.forms import EventForm, AddMemberForm


def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split("-"))
        return date(year, month, day=1)
    return datetime.today()


def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = "month=" + str(prev_month.year) + "-" + str(prev_month.month)
    return month


def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = "month=" + str(next_month.year) + "-" + str(next_month.month)
    return month


class CalendarView(LoginRequiredMixin, generic.ListView):
    login_url = "accounts:signin"
    model = Event
    template_name = "calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = get_date(self.request.GET.get("month", None))
        cal = Calendar(d.year, d.month)
        html_cal = cal.formatmonth(withyear=True)
        context["calendar"] = mark_safe(html_cal)
        context["prev_month"] = prev_month(d)
        context["next_month"] = next_month(d)
        return context


@login_required(login_url="signup")
def create_event(request):
    form = EventForm(request.POST or None)
    if request.POST and form.is_valid():
        title = form.cleaned_data["title"]
        head = form.cleaned_data.get("head")
        importance = form.cleaned_data.get("importance")
        location = form.cleaned_data.get("location")
        start_time = form.cleaned_data["start_time"]
        end_time = form.cleaned_data["end_time"]
        # prevent creating events that overlap existing events for this user
        conflict_exists = Event.objects.filter(
            user=request.user,
            is_active=True,
            is_deleted=False,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists()

        if conflict_exists:
            # attach a non-field error so the template can show it
            form.add_error(None, "This event conflicts with an existing event and cannot be created.")
        else:
            Event.objects.create(
                user=request.user,
                title=title,
                head=head,
                importance=importance,
                location=location,
                start_time=start_time,
                end_time=end_time,
            )
            return HttpResponseRedirect(reverse("calendarapp:calendar"))
    return render(request, "event.html", {"form": form})


class EventEdit(generic.UpdateView):
    model = Event
    fields = ["title", "head", "importance", "location", "start_time", "end_time"]
    template_name = "event.html"


@login_required(login_url="signup")
def event_details(request, event_id):
    event = Event.objects.get(id=event_id)
    eventmember = EventMember.objects.filter(event=event)
    context = {"event": event, "eventmember": eventmember}
    return render(request, "event-details.html", context)


def add_eventmember(request, event_id):
    forms = AddMemberForm()
    if request.method == "POST":
        forms = AddMemberForm(request.POST)
        if forms.is_valid():
            member = EventMember.objects.filter(event=event_id)
            event = Event.objects.get(id=event_id)
            if member.count() <= 9:
                user = forms.cleaned_data["user"]
                EventMember.objects.create(event=event, user=user)
                return redirect("calendarapp:calendar")
            else:
                print("--------------User limit exceed!-----------------")
    context = {"form": forms}
    return render(request, "add_member.html", context)


class EventMemberDeleteView(generic.DeleteView):
    model = EventMember
    template_name = "event_delete.html"
    success_url = reverse_lazy("calendarapp:calendar")

class CalendarViewNew(LoginRequiredMixin, generic.View):
    login_url = "accounts:signin"
    template_name = "calendarapp/calendar.html"
    form_class = EventForm

    def get(self, request, *args, **kwargs):
        forms = self.form_class()
        events = Event.objects.get_all_events(user=request.user)
        events_month = Event.objects.get_running_events(user=request.user)
        event_list = []
        # start: '2020-09-16T16:00:00'
        for event in events:
            # map importance to colors so calendar visually reflects priority
            if event.importance == "high":
                bg = "#ff6b6b"
                border = "#ff4c4c"
            elif event.importance == "normal":
                bg = "#ffd166"
                border = "#ffbf4d"
            else:
                bg = "#8ecae6"
                border = "#61a5c2"

            event_list.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "start": event.start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end": event.end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "head": event.head,
                    "importance": event.importance,
                    "location": event.location,
                    "backgroundColor": bg,
                    "borderColor": border,
                }
            )
        
        context = {"form": forms, "events": event_list,
                   "events_month": events_month}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        forms = self.form_class(request.POST)
        if forms.is_valid():
            # check for conflicts before saving
            start_time = forms.cleaned_data.get("start_time")
            end_time = forms.cleaned_data.get("end_time")
            conflict_exists = Event.objects.filter(
                user=request.user,
                is_active=True,
                is_deleted=False,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).exists()

            if conflict_exists:
                forms.add_error(None, "This event conflicts with an existing event and cannot be created.")
            else:
                form = forms.save(commit=False)
                form.user = request.user
                form.save()
                return redirect("calendarapp:calendar")
        context = {"form": forms}
        return render(request, self.template_name, context)



def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        event.delete()
        return JsonResponse({'message': 'Event sucess delete.'})
    else:
        return JsonResponse({'message': 'Error!'}, status=400)

def next_week(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        # create a copy moving the event one week forward but prevent conflicts
        new_start = event.start_time + timedelta(days=7)
        new_end = event.end_time + timedelta(days=7)
        conflict_exists = Event.objects.filter(
            user=event.user,
            is_active=True,
            is_deleted=False,
            start_time__lt=new_end,
            end_time__gt=new_start,
        ).exists()

        if conflict_exists:
            return JsonResponse({'message': 'Cannot add event in next week: it conflicts with an existing event.'}, status=400)

        new_event = Event(
            user=event.user,
            title=event.title,
            head=event.head,
            importance=event.importance,
            location=event.location,
            start_time=new_start,
            end_time=new_end,
        )
        new_event.save()
        return JsonResponse({'message': 'Sucess!'})
    else:
        return JsonResponse({'message': 'Error!'}, status=400)

def next_day(request, event_id):

    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        new_start = event.start_time + timedelta(days=1)
        new_end = event.end_time + timedelta(days=1)
        conflict_exists = Event.objects.filter(
            user=event.user,
            is_active=True,
            is_deleted=False,
            start_time__lt=new_end,
            end_time__gt=new_start,
        ).exists()

        if conflict_exists:
            return JsonResponse({'message': 'Cannot add event next day: it conflicts with an existing event.'}, status=400)

        new_event = Event(
            user=event.user,
            title=event.title,
            head=event.head,
            importance=event.importance,
            location=event.location,
            start_time=new_start,
            end_time=new_end,
        )
        new_event.save()
        return JsonResponse({'message': 'Sucess!'})
    else:
        return JsonResponse({'message': 'Error!'}, status=400)
