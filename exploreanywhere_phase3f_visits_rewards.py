#!/usr/bin/env python3
"""ExploreAnywhere Phase 3F: staff-reviewed visit check-ins and earned rewards.

Run from the Django project root (activated venv), after Phase 3E.
This file only installs source code and creates backups. It does NOT create
DB tables or run migrations. Run Django migration commands separately.
"""
from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()
MARK = 'ExploreAnywhere phase3f visits-and-rewards v1'
SETTINGS = Path('mysite/settings.py')
ROOT_URLS = Path('mysite/urls.py')
JOURNEY_VIEWS = Path('apps/places/journey_views.py')
DETAIL = Path('templates/places/place_detail.html')
DASHBOARD = Path('templates/places/journey_dashboard.html')
APP = Path('apps/visits')

APP_FILES = {
    APP / '__init__.py': '',
    APP / 'migrations/__init__.py': '',
    APP / 'apps.py': '''from django.apps import AppConfig

class VisitsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.visits"
    verbose_name = "Kabankalan visit check-ins"
''',
    APP / 'models.py': r'''"""Staff-reviewed check-in records; a self-report is not proof of presence."""
from django.conf import settings
from django.db import models


class VisitCheckIn(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending staff review"
        APPROVED = "approved", "Staff approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="kabankalan_checkins",
    )
    place = models.ForeignKey(
        "places.Place", on_delete=models.CASCADE,
        related_name="visitor_checkins",
    )
    visited_on = models.DateField()
    visit_note = models.TextField(max_length=1000)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="moderated_kabankalan_checkins",
    )
    reviewer_note = models.TextField(blank=True)

    class Meta:
        db_table = "explore_visit_checkins"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "place"], name="unique_visit_user_place",
            ),
        ]
        ordering = ["-submitted_at", "-pk"]

    def __str__(self):
        return f"{self.user} / {self.place} / {self.status}"
''',
    APP / 'services.py': r'''"""Rewards are derived from staff-approved unique destinations, never self-reports."""
BADGE_RULES = (
    ("First Explorer", 1, "First staff-approved destination"),
    ("Trail Collector", 3, "Three staff-approved destinations"),
    ("Kabankalan Pathfinder", 5, "Five staff-approved destinations"),
)
POINTS_PER_APPROVED_PLACE = 100


def visit_rewards(approved_count):
    count = max(0, int(approved_count))
    return {
        "points": count * POINTS_PER_APPROVED_PLACE,
        "badges": [
            {"name": name, "required": requirement, "description": description,
             "earned": count >= requirement}
            for name, requirement, description in BADGE_RULES
        ],
    }
''',
    APP / 'views.py': r'''"""Kabankalan-only, authenticated check-ins with manual staff review."""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from apps.places.models import Place
from .models import VisitCheckIn
from .services import visit_rewards

CITY_ID = 2
MIN_NOTE_LENGTH = 20
MAX_NOTE_LENGTH = 1000


def _published():
    return Place.objects.filter(city_id=CITY_ID, is_active=True, is_verified=True)


@login_required
@require_http_methods(['GET', 'POST'])
def check_in(request, pk):
    place = get_object_or_404(_published(), pk=pk)
    previous = VisitCheckIn.objects.filter(user=request.user, place=place).first()
    today = timezone.localdate()

    if request.method == 'POST':
        note = (request.POST.get('visit_note') or '').strip()
        visit_date_raw = (request.POST.get('visited_on') or '').strip()
        try:
            visit_date = date.fromisoformat(visit_date_raw)
        except (ValueError, TypeError):
            messages.error(request, 'Enter a valid visit date.')
            return redirect('visits:check_in', pk=pk)
        if visit_date > today or visit_date < date(2020, 1, 1):
            messages.error(request, 'The visit date must be between 2020 and today.')
            return redirect('visits:check_in', pk=pk)
        if not MIN_NOTE_LENGTH <= len(note) <= MAX_NOTE_LENGTH:
            messages.error(request, 'Provide a 20–1,000 character visit note for review.')
            return redirect('visits:check_in', pk=pk)

        # One submitted visit per user and destination; resubmit only if rejected.
        with transaction.atomic():
            checkin, created = VisitCheckIn.objects.select_for_update().get_or_create(
                user=request.user,
                place=place,
                defaults={"visited_on": visit_date, "visit_note": note},
            )
            if created:
                messages.success(request, 'Check-in submitted for staff review. No points awarded yet.')
            elif checkin.status == VisitCheckIn.Status.REJECTED:
                checkin.visited_on = visit_date
                checkin.visit_note = note
                checkin.status = VisitCheckIn.Status.PENDING
                checkin.reviewed_at = None
                checkin.reviewed_by = None
                checkin.reviewer_note = ''
                checkin.save(update_fields=[
                    'visited_on', 'visit_note', 'status', 'reviewed_at',
                    'reviewed_by', 'reviewer_note',
                ])
                messages.success(request, 'Your corrected check-in was submitted for review.')
            else:
                messages.info(request, 'This destination already has a pending or approved check-in.')
        return redirect('visits:list')

    return render(request, 'visits/check_in.html', {
        'place': place, 'checkin': previous, 'today': today,
    })


@login_required
@require_GET
def my_visits(request):
    entries = (VisitCheckIn.objects
        .filter(user=request.user, place__city_id=CITY_ID)
        .select_related('place').order_by('-submitted_at'))
    approved_count = entries.filter(status=VisitCheckIn.Status.APPROVED).count()
    pending_count = entries.filter(status=VisitCheckIn.Status.PENDING).count()
    rewards = visit_rewards(approved_count)
    return render(request, 'visits/my_visits.html', {
        'entries': entries, 'approved_count': approved_count,
        'pending_count': pending_count, 'reward_points': rewards['points'],
        'badges': rewards['badges'],
    })
''',
    APP / 'urls.py': r'''from django.urls import path
from . import views

app_name = 'visits'

urlpatterns = [
    path('', views.my_visits, name='list'),
    path('check-in/<int:pk>/', views.check_in, name='check_in'),
]
''',
    APP / 'admin.py': r'''"""Moderate visitor check-ins. Approval requires external corroboration by staff."""
from django.contrib import admin
from django.utils import timezone
from .models import VisitCheckIn


@admin.register(VisitCheckIn)
class VisitCheckInAdmin(admin.ModelAdmin):
    list_display = ('user', 'place', 'visited_on', 'status', 'submitted_at', 'reviewed_by')
    list_filter = ('status', 'visited_on')
    search_fields = ('user__username', 'place__title', 'visit_note')
    list_select_related = ('user', 'place', 'reviewed_by')
    readonly_fields = (
        'user', 'place', 'visited_on', 'visit_note', 'status',
        'submitted_at', 'reviewed_at', 'reviewed_by',
    )
    actions = ('approve_reviewed', 'reject_reviewed', 'revoke_approval')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(place__city_id=2)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description='Approve independently corroborated pending check-ins', permissions=['change'])
    def approve_reviewed(self, request, queryset):
        # Staff must first write >=20 characters explaining independent
        # corroboration in reviewer_note on each check-in's admin detail page.
        eligible = [entry.pk for entry in queryset.filter(
            status=VisitCheckIn.Status.PENDING, place__city_id=2
        ) if len(entry.reviewer_note.strip()) >= 20]
        count = VisitCheckIn.objects.filter(pk__in=eligible,
            status=VisitCheckIn.Status.PENDING, place__city_id=2).update(
            status=VisitCheckIn.Status.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request,
            f'Approved {count} check-in(s). Others need a 20+ character reviewer note describing independent corroboration.')

    @admin.action(description='Reject pending check-ins', permissions=['change'])
    def reject_reviewed(self, request, queryset):
        count = queryset.filter(status=VisitCheckIn.Status.PENDING, place__city_id=2).update(
            status=VisitCheckIn.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f'Rejected {count} pending check-in(s).')

    @admin.action(description='Revoke previously approved check-ins', permissions=['change'])
    def revoke_approval(self, request, queryset):
        # If evidence is later invalidated, rewards disappear automatically.
        count = queryset.filter(status=VisitCheckIn.Status.APPROVED, place__city_id=2).update(
            status=VisitCheckIn.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f'Revoked {count} approved check-in(s).')
''',
    Path('templates/visits/check_in.html'): r'''{% extends "theme/public_base.html" %}
{% block extra_css %}
<style>
.ea-checkin{max-width:840px;margin:auto;padding:44px 20px 90px;color:#183454}
.ea-checkin h1{font-size:clamp(27px,4vw,40px);color:#102f5b;margin:8px 0 12px}
.ea-checkin p{color:#5c718d;line-height:1.7}
.ea-checkin-card{background:white;border:1px solid #dce7f3;border-radius:18px;padding:24px;margin-top:22px}
.ea-checkin label{display:block;font-weight:700;color:#173d6c;margin:14px 0 6px}
.ea-checkin input,.ea-checkin textarea{display:block;box-sizing:border-box;width:100%;border:1px solid #b7cce5;border-radius:10px;padding:12px;font:inherit}
.ea-checkin textarea{min-height:125px;resize:vertical}
.ea-checkin-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}
.ea-checkin-btn{border:0;background:#075ee4;color:#fff!important;padding:12px 19px;border-radius:11px;font-weight:750;text-decoration:none;cursor:pointer;display:inline-block}
.ea-checkin-btn.secondary{color:#075ee4!important;background:#fff;border:1px solid #c5d8f0}
.ea-checkin-note{background:#eef5fd;color:#375575;border-radius:12px;padding:15px;margin-top:18px}
</style>
{% endblock %}
{% block content %}
<main class="ea-checkin">
  <p>MY KABANKALAN JOURNEY</p>
  <h1>Report a Visit: {{ place.title }}</h1>
  <p>Only submit a check-in for a destination you visited in person. Your report starts as pending and does not earn points until staff reviews and approves it using independent evidence.</p>
  <nav class="ea-checkin-actions"><a class="ea-checkin-btn secondary" href="{% url 'places:place_detail' place.pk %}">Place Details</a><a class="ea-checkin-btn secondary" href="{% url 'visits:list' %}">My Visits</a></nav>
  <section class="ea-checkin-card">
    {% if checkin and checkin.status == 'approved' %}
      <h2>Staff-approved check-in</h2><p>Your check-in for {{ checkin.visited_on }} has been approved by staff. A maximum of one approved visit is counted per destination.</p>
    {% elif checkin and checkin.status == 'pending' %}
      <h2>Pending staff review</h2><p>Your report from {{ checkin.visited_on }} has been submitted and is waiting for staff review. No points or badges have been earned from this check-in yet.</p>
    {% else %}
      {% if checkin and checkin.status == 'rejected' %}<h2>Resubmit your visit</h2><p>The earlier check-in was rejected. Please correct the information before trying again.</p>{% else %}<h2>Submit your check-in</h2>{% endif %}
      <form method="post" action="{% url 'visits:check_in' place.pk %}">
        {% csrf_token %}
        <label for="visit-date">Date you visited</label>
        <input id="visit-date" name="visited_on" type="date" value="{{ today|date:'Y-m-d' }}" max="{{ today|date:'Y-m-d' }}" min="2020-01-01" required>
        <label for="visit-note">Visit note for staff review (20–1,000 characters)</label>
        <textarea id="visit-note" name="visit_note" minlength="20" maxlength="1000" required placeholder="Describe your activity and any information staff can independently corroborate.">{% if checkin %}{{ checkin.visit_note }}{% endif %}</textarea>
        <p class="ea-checkin-note">A written note is not proof of presence. Staff must corroborate your visit separately. Location access is not requested or recorded.</p>
        <div class="ea-checkin-actions"><button class="ea-checkin-btn" type="submit">Submit for Staff Review</button></div>
      </form>
    {% endif %}
  </section>
</main>
{% endblock %}
''',
    Path('templates/visits/my_visits.html'): r'''{% extends "theme/public_base.html" %}
{% block extra_css %}
<style>
.ea-visits{max-width:1100px;margin:auto;padding:44px 20px 90px;color:#183454}
.ea-visits h1{font-size:clamp(29px,4vw,42px);font-weight:800;color:#102f5b;margin:8px 0}
.ea-visits p{color:#5e728b;line-height:1.6}
.ea-visits-nav{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}
.ea-visits-link{background:#075ee4;color:#fff!important;padding:11px 16px;text-decoration:none;border-radius:10px;display:inline-block;font-weight:750}
.ea-visits-link.alt{color:#0757d8!important;background:#fff;border:1px solid #c8d9ed}
.ea-visits-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:25px 0}
.ea-visits-stat{background:#fff;border:1px solid #dce7f3;border-radius:15px;padding:21px}
.ea-visits-stat strong{display:block;font-size:30px;color:#0757d8}
.ea-visits-stat span{color:#597087;font-size:13px}
.ea-visit-card{border:1px solid #dce7f3;border-radius:16px;background:#fff;margin:14px 0;padding:22px}
.ea-visit-card h2{font-size:20px;margin:0 0 7px}
.ea-visit-status{font-size:12px;font-weight:800;padding:5px 10px;border-radius:999px;background:#f1f5f9;color:#334155;display:inline-block}
.ea-visit-status.approved{background:#dcfce7;color:#166534}
.ea-visit-status.pending{background:#fef3c7;color:#92400e}
.ea-visit-status.rejected{background:#fee2e2;color:#991b1b}
.ea-visit-badges{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin:18px 0}
.ea-visit-badge{border-radius:13px;border:1px solid #d5e0ef;padding:16px;background:#f9fbff}
.ea-visit-badge.earned{border-color:#9dd6b6;background:#f1fcf6}
.ea-visit-badge strong{display:block;margin-bottom:5px}
.ea-empty{border:1px dashed #cbd8e9;background:white;border-radius:16px;padding:27px}
</style>
{% endblock %}
{% block content %}
<main class="ea-visits">
  <p>ONE CITY. YOUR HOBBIES. OUR MAP.</p><h1>My Kabankalan Visits</h1>
  <p>Only staff-approved destination check-ins earn points and badges. A visit report, saved place, map view, or submitted review does not verify physical presence.</p>
  <nav class="ea-visits-nav"><a class="ea-visits-link" href="{% url 'places:journey_dashboard' %}">My Journey</a><a class="ea-visits-link alt" href="{% url 'places:attraction_carousel' %}">Explore Places</a></nav>
  <section class="ea-visits-stats" aria-label="Visit statistics">
    <div class="ea-visits-stat"><strong>{{ approved_count }}</strong><span>Staff-approved destinations</span></div>
    <div class="ea-visits-stat"><strong>{{ pending_count }}</strong><span>Pending check-ins</span></div>
    <div class="ea-visits-stat"><strong>{{ reward_points }}</strong><span>Points from approved visits</span></div>
  </section>
  <h2>My Badges</h2>
  <section class="ea-visit-badges" aria-label="Earned and future badges">
    {% for badge in badges %}
      <div class="ea-visit-badge {% if badge.earned %}earned{% endif %}"><strong>{% if badge.earned %}Earned: {% else %}Locked: {% endif %}{{ badge.name }}</strong><p>{{ badge.description }}</p></div>
    {% endfor %}
  </section>
  <h2>Check-in History</h2>
  {% for visit in entries %}
    <article class="ea-visit-card">
      <h2>{{ visit.place.title }}</h2><p>Visited on {{ visit.visited_on|date:'M j, Y' }}</p>
      <span class="ea-visit-status {{ visit.status }}">{{ visit.get_status_display }}</span>
      <p>{{ visit.visit_note|linebreaksbr }}</p>
      {% if visit.status == 'rejected' and visit.place.is_active and visit.place.is_verified %}<p><a class="ea-visits-link alt" href="{% url 'visits:check_in' visit.place.pk %}">Correct and Resubmit</a></p>{% endif %}
      {% if visit.place.is_active and visit.place.is_verified %}<a class="ea-visits-link alt" href="{% url 'places:place_detail' visit.place.pk %}">View Destination</a>{% endif %}
    </article>
  {% empty %}
    <section class="ea-empty"><h2>No visits reported yet</h2><p>Open an eligible Kabankalan place and use Report a Visit to submit a check-in.</p></section>
  {% endfor %}
</main>
{% endblock %}
''',
}

VISITS_JOURNEY_BLOCK = r'''<section class="ea-journey-panel">
      <h2>My Visits</h2>
      <p><strong>{{ approved_visit_count }}</strong> staff-approved destination{{ approved_visit_count|pluralize }}; <strong>{{ pending_visit_count }}</strong> pending check-in{{ pending_visit_count|pluralize }}.</p>
      <p class="ea-journey-note">Self-reported visits are not verified automatically. Staff review requires independent corroboration.</p>
      {% for visit in visits_preview %}
        <p>{{ visit.place.title }} — {{ visit.get_status_display }}</p>
      {% empty %}
        <p>No visits reported yet.</p>
      {% endfor %}
      <a class="ea-journey-link" href="{% url 'visits:list' %}">My Visits</a>
    </section>'''

REWARDS_JOURNEY_BLOCK = r'''<section class="ea-journey-panel">
      <h2>Badges and Points</h2>
      <p><strong>{{ visit_points }}</strong> points earned from staff-approved destination check-ins.</p>
      {% for badge in visit_badges %}
        <p>{% if badge.earned %}Earned{% else %}Locked{% endif %}: <strong>{{ badge.name }}</strong> — {{ badge.description }}</p>
      {% endfor %}
      <a class="ea-journey-link" href="{% url 'visits:list' %}">View Achievements</a>
    </section>'''


def fail(message):
    raise RuntimeError(message)


def replace_once(source, before, after, description):
    count = source.count(before)
    if count != 1:
        fail(f'{description}: expected one exact insertion point, found {count}.')
    return source.replace(before, after, 1)


def main():
    required = (SETTINGS, ROOT_URLS, JOURNEY_VIEWS, DETAIL, DASHBOARD,
                Path('apps/places/models.py'), Path('apps/visits'))
    for p in required[:-1]:
        if not (ROOT / p).is_file():
            fail(f'Missing {p}. Run from the ExploreAnywhere Django project root.')
    if (ROOT / APP).exists():
        fail('apps/visits already exists. Stopped to avoid overwriting work or duplicating an installation.')
    # A legacy project with database tables but no migration history can fail
    # when a new app references its User and Place models. Never make changes
    # until that migration foundation has been explicitly checked.
    missing_histories = []
    for app_name in ('users', 'places'):
        folder = ROOT / 'apps' / app_name / 'migrations'
        numbered = (list(folder.glob('[0-9][0-9][0-9][0-9]_*.py'))
                    if folder.is_dir() else [])
        if not numbered:
            missing_histories.append(app_name)
    if missing_histories:
        fail('Migration history not established for: ' + ', '.join(missing_histories)
             + '. No files changed. Run: python manage.py showmigrations users places'
             + ' and share the output before adding a new cross-app migration.')

    sources = {p: (ROOT / p).read_text(encoding='utf-8-sig')
               for p in (SETTINGS, ROOT_URLS, JOURNEY_VIEWS, DETAIL, DASHBOARD)}
    settings, urls, journey, detail, dashboard = (sources[p] for p in
        (SETTINGS, ROOT_URLS, JOURNEY_VIEWS, DETAIL, DASHBOARD))
    if any(MARK in val for val in sources.values()) or 'apps.visits' in settings:
        fail('Phase 3F appears installed already.')
    if 'class Place(' not in (ROOT / 'apps/places/models.py').read_text(encoding='utf-8-sig'):
        fail('The audited Place model was not found.')
    if 'apps.itineraries' not in settings:
        fail('Expected installed itinerary app was not found.')
    if 'from django.urls import' not in urls or 'include' not in urls:
        fail('Project URLs differ from the earlier verified project.')
    if not re.search(r'(?m)^urlpatterns\s*=\s*\[', urls):
        fail('Cannot safely find the project URL configuration.')
    if '"review_count": review_count,' not in journey or '"my_reviews_preview":' not in journey:
        fail('Phase 3E dashboard context not found. Stop rather than overwriting.')
    if '<h2>My Visits</h2>' not in dashboard or '<h2>Badges and Points</h2>' not in dashboard:
        fail('My Journey dashboard placeholders changed. Please upload your latest template.')

    app_line = re.search(r'(?m)^([ \t]*)([\'\"])apps\.itineraries\2\s*,', settings)
    if not app_line:
        fail('Cannot find a unique existing itinerary app line in INSTALLED_APPS.')
    settings_new = (settings[:app_line.end()] + '\n' + app_line.group(1) +
                    "'apps.visits.apps.VisitsConfig',  # " + MARK + settings[app_line.end():])
    match = re.search(r'(?m)^urlpatterns\s*=\s*\[', urls)
    urls_new = (urls[:match.end()] + "\n    path('visits/', include('apps.visits.urls')),  # " +
                MARK + urls[match.end():])

    anchor = '    return render(request, "places/journey_dashboard.html", {'
    context_prelude = '''    # ''' + MARK + '''
    from apps.visits.models import VisitCheckIn
    from apps.visits.services import visit_rewards
    my_checkins = (VisitCheckIn.objects.filter(user=request.user, place__city_id=2)
                   .select_related("place").order_by("-submitted_at"))
    approved_visit_count = my_checkins.filter(status=VisitCheckIn.Status.APPROVED).count()
    pending_visit_count = my_checkins.filter(status=VisitCheckIn.Status.PENDING).count()
    visit_rewards_data = visit_rewards(approved_visit_count)
'''
    journey_new = replace_once(journey, anchor, context_prelude + anchor, 'Journey query insert')
    context_anchor = '        "review_count": review_count,'
    context_add = '''        "approved_visit_count": approved_visit_count,
        "pending_visit_count": pending_visit_count,
        "visit_points": visit_rewards_data["points"],
        "visit_badges": visit_rewards_data["badges"],
        "visits_preview": my_checkins[:3],
'''
    journey_new = replace_once(journey_new, context_anchor,
                               context_anchor + '\n' + context_add.rstrip(), 'Journey context')

    # Replace only the original Phase 3 placeholder cards, leaving reviews and trips alone.
    visits_pattern = re.compile(r'<section class="ea-journey-panel">\s*<h2>My Visits</h2>.*?</section>', re.S)
    rewards_pattern = re.compile(r'<section class="ea-journey-panel">\s*<h2>Badges and Points</h2>.*?</section>', re.S)
    if len(visits_pattern.findall(dashboard)) != 1 or len(rewards_pattern.findall(dashboard)) != 1:
        fail('Expected exactly one original Visits and one Badges placeholder card.')
    dashboard_new = visits_pattern.sub(lambda _: VISITS_JOURNEY_BLOCK, dashboard, count=1)
    dashboard_new = rewards_pattern.sub(lambda _: REWARDS_JOURNEY_BLOCK, dashboard_new, count=1)
    dashboard_new = dashboard_new.replace('grid-template-columns:repeat(3,minmax(0,1fr))',
                                          'grid-template-columns:repeat(auto-fit,minmax(165px,1fr))', 1)

    detail_link = '<a href="{% url \'places:journey_dashboard\' %}">My Journey</a>'
    detail_new = replace_once(detail, detail_link,
                              detail_link + '\n      <a href="{% url \'visits:check_in\' place.pk %}">Report a Visit</a>',
                              'Place Details link')

    modifications = {
        SETTINGS: settings_new,
        ROOT_URLS: urls_new,
        JOURNEY_VIEWS: journey_new,
        DETAIL: detail_new,
        DASHBOARD: dashboard_new,
        **APP_FILES,
    }
    for p, content in modifications.items():
        if p.suffix == '.py':
            ast.parse(content, filename=str(p))
        if p.suffix == '.html':
            if content.count('{% block content %}') != 1 or content.count('{% endblock %}') < 2:
                fail(f'Unexpected Django template structure in {p}.')

    backup = ROOT / 'phase3_backups' / ('visits-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=False)
    original = {p: (ROOT / p).is_file() for p in modifications}
    for p, existed in original.items():
        if existed:
            backup_file = backup / p
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / p, backup_file)

    touched = []
    try:
        for p, content in modifications.items():
            target = ROOT / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8', newline='\n')
            touched.append(p)
    except Exception:
        for p in reversed(touched):
            if original[p]:
                shutil.copy2(backup / p, ROOT / p)
            else:
                (ROOT / p).unlink(missing_ok=True)
        raise
    print('SUCCESS: Phase 3F code installed (database migration still required).')
    print('Added staff-reviewed check-ins, self-reported visit history, and reward calculation.')
    print('No database tables or records were modified by installation.')
    print('Backups:', backup.relative_to(ROOT))
    print('Next: python manage.py makemigrations visits')
    print('Next: python manage.py sqlmigrate visits 0001')
    print('Next: python manage.py migrate visits')
    print('Next: python manage.py check')
    print('Routes: /visits/ and /visits/check-in/<place_id>/')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('STOPPED:', exc, file=sys.stderr)
        sys.exit(1)
