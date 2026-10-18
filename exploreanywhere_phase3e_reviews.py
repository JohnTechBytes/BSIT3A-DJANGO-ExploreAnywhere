#!/usr/bin/env python3
"""ExploreAnywhere Phase 3E — safe reviews integration.

Run from the Django project root on Windows using your activated venv.
No database migrations and no automatic database writes.
"""
from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
import shutil
import sys

ROOT = Path.cwd()
URLS = Path('apps/places/urls.py')
VIEWS = Path('apps/places/views.py')
MODELS = Path('apps/places/models.py')
REVIEW_VIEWS = Path('apps/places/review_views.py')
JOURNEY_VIEWS = Path('apps/places/journey_views.py')
DETAIL = Path('templates/places/place_detail.html')
DASHBOARD = Path('templates/places/journey_dashboard.html')
MY_REVIEWS = Path('templates/places/my_reviews.html')
MARK = 'ExploreAnywhere phase3e reviews v1'

REVIEW_CODE = r'''"""ExploreAnywhere Phase 3E: user-owned Kabankalan reviews."""
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Place, Review

CITY_ID = 2
MAX_COMMENT_LENGTH = 1500


def _published():
    return Place.objects.filter(city_id=CITY_ID, is_active=True, is_verified=True)


def _sync_rating(place):
    # Call only inside the transaction while holding the Place row lock.
    aggregate = Review.objects.filter(place=place).aggregate(
        total=Count('pk'), mean=Avg('rating'))
    mean = aggregate['mean']
    place.review_count = aggregate['total'] or 0
    place.avg_rating = (Decimal(str(mean)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP) if mean is not None
        else Decimal('0.00'))
    place.save(update_fields=['review_count', 'avg_rating'])


@login_required
@require_POST
def submit_review(request, pk):
    # Reject tampered ratings and oversized comments, without changing records.
    rating_text = (request.POST.get('rating') or '').strip()
    comment = (request.POST.get('comment') or '').strip()
    if rating_text not in {'1', '2', '3', '4', '5'}:
        messages.error(request, 'Choose a rating from 1 to 5 stars.')
        return redirect('places:place_detail', pk=pk)
    if len(comment) > MAX_COMMENT_LENGTH:
        messages.error(request, 'Review comment must be at most 1,500 characters.')
        return redirect('places:place_detail', pk=pk)

    # Lock place row to serialize our review mutations for this destination.
    with transaction.atomic():
        place = get_object_or_404(_published().select_for_update(), pk=pk)
        review = (Review.objects.filter(user=request.user, place=place)
                  .order_by('pk').first())
        if review is None:
            Review.objects.create(user=request.user, place=place,
                                  rating=int(rating_text), comment=comment)
            messages.success(request, 'Your review was submitted.')
        else:
            review.rating = int(rating_text)
            review.comment = comment
            review.save(update_fields=['rating', 'comment'])
            messages.success(request, 'Your review was updated.')
        _sync_rating(place)
    return redirect('places:place_detail', pk=pk)


@login_required
@require_POST
def delete_review(request, pk):
    with transaction.atomic():
        place = get_object_or_404(Place.objects.filter(city_id=CITY_ID)
                                  .select_for_update(), pk=pk)
        deleted, _ = Review.objects.filter(user=request.user, place=place).delete()
        if deleted:
            _sync_rating(place)
            messages.success(request, 'Your review was deleted.')
    if place.is_active and place.is_verified:
        return redirect('places:place_detail', pk=pk)
    return redirect('places:my_reviews')


@login_required
def my_reviews(request):
    reviews = (Review.objects.filter(user=request.user, place__city_id=CITY_ID)
               .select_related('place', 'place__category').order_by('-created_at'))
    return render(request, 'places/my_reviews.html', {'reviews': reviews})
'''

CSS_DETAIL = r'''
/* ExploreAnywhere phase3e reviews v1 */
.ea-reviews {margin-top:26px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px}
.ea-reviews-panel {background:white;border:1px solid #dce7f3;border-radius:18px;padding:24px;min-width:0}
.ea-reviews-panel h2 {font-size:21px;font-weight:800;color:#12345b;margin:0 0 8px}
.ea-review-muted {color:#62758c;font-size:13px;line-height:1.6;margin:5px 0 12px}
.ea-review-rating {color:#0e55b5;font-weight:800}
.ea-review-stars {display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}
.ea-review-stars label {cursor:pointer;display:inline-flex;align-items:center;gap:4px;border:1px solid #d6e2f0;border-radius:10px;padding:9px 12px;color:#1c4d86;font-weight:700}
.ea-review-stars label:has(input:checked) {border-color:#075ee4;background:#eaf3ff}
.ea-review-stars input {accent-color:#075ee4}
.ea-review-textarea {box-sizing:border-box;width:100%;min-height:106px;padding:12px;border:1px solid #becfe5;border-radius:11px;font:inherit;resize:vertical}
.ea-review-btn {background:#075ee4;color:white;border:0;border-radius:11px;padding:12px 17px;font:inherit;font-weight:750;cursor:pointer}
.ea-review-delete {background:white;color:#a02032;border:1px solid #eabac1}
.ea-review-actions {display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}
.ea-review-card {border-top:1px solid #e9eef5;padding:14px 0}
.ea-review-card strong {color:#153c67}
.ea-review-card p {margin:5px 0 0;color:#526983;overflow-wrap:anywhere}
.ea-review-card small {color:#697d96}
.ea-review-note {background:#eef4fb;padding:11px 13px;border-radius:10px;color:#4b6280;font-size:12px;margin-top:12px}
.ea-review-link {color:#0757d8;font-weight:700;text-decoration:none}
@media(max-width:760px){.ea-reviews{grid-template-columns:1fr}}
'''

HTML_DETAIL = r'''
<!-- ExploreAnywhere phase3e reviews v1 -->
<section class="ea-reviews" aria-label="Destination reviews" id="place-reviews">
  <div class="ea-reviews-panel">
    <h2>Ratings &amp; Reviews</h2>
    {% if place.review_count %}
      <p class="ea-review-rating">{{ place.avg_rating|floatformat:2 }} / 5 stars · {{ place.review_count }} review{{ place.review_count|pluralize }}</p>
    {% else %}
      <p class="ea-review-muted">No ratings yet. Be the first to review this place.</p>
    {% endif %}
    {% for review in public_reviews %}
      <article class="ea-review-card">
        <strong>{{ review.rating }} / 5 stars</strong> · <span>{{ review.user.username }}</span>
        <small> · {{ review.created_at|date:"M j, Y" }}</small>
        {% if review.comment %}<p>{{ review.comment|linebreaksbr }}</p>{% endif %}
      </article>
    {% empty %}
      <p class="ea-review-muted">Reviews from visitors will appear here.</p>
    {% endfor %}
  </div>
  <div class="ea-reviews-panel">
    <h2>{% if my_review %}Update Your Review{% else %}Write a Review{% endif %}</h2>
    <p class="ea-review-muted">Your rating helps other people discover Kabankalan destinations.</p>
    <form method="post" action="{% url 'places:submit_review' place.pk %}">
      {% csrf_token %}
      <fieldset style="border:0;padding:0;margin:0">
        <legend class="ea-review-muted">Choose a rating (required)</legend>
        <div class="ea-review-stars">
          {% for value in review_rating_options %}
            <label><input type="radio" name="rating" value="{{ value }}" required {% if my_review.rating == value %}checked{% endif %}>{{ value }} ★</label>
          {% endfor %}
        </div>
      </fieldset>
      <label for="ea-review-comment" class="ea-review-muted">Your experience (optional; up to 1,500 characters)</label>
      <textarea class="ea-review-textarea" id="ea-review-comment" name="comment" maxlength="1500" placeholder="What should other Kabankalan explorers know?">{{ my_review.comment|default_if_none:"" }}</textarea>
      <div class="ea-review-actions"><button class="ea-review-btn" type="submit">{% if my_review %}Update Review{% else %}Submit Review{% endif %}</button></div>
    </form>
    {% if my_review %}
      <form method="post" action="{% url 'places:delete_review' place.pk %}" onsubmit="return confirm('Delete your review?');">
        {% csrf_token %}
        <div class="ea-review-actions"><button class="ea-review-btn ea-review-delete" type="submit">Delete My Review</button></div>
      </form>
    {% endif %}
    <p class="ea-review-note">Reviews are personal opinions. Submitting a review does not verify an in-person visit.</p>
    <a class="ea-review-link" href="{% url 'places:my_reviews' %}">View My Reviews →</a>
  </div>
</section>
'''

MY_REVIEWS_HTML = r'''{% extends "theme/public_base.html" %}
{% block extra_css %}
<style>
.ea-myreviews{max-width:960px;padding:44px 20px 90px;margin:0 auto;color:#173454}
.ea-myreviews h1{font-size:clamp(29px,4vw,40px);margin:10px 0 8px;color:#102f56;font-weight:850}
.ea-myreviews p{color:#60718b;line-height:1.6}
.ea-myr-card{background:#fff;border:1px solid #dfe8f4;border-radius:16px;padding:22px;margin:14px 0}
.ea-myr-card h2{font-size:20px;margin:0 0 5px;color:#153d69}
.ea-myr-stars{color:#0757d8;font-weight:800}
.ea-myr-actions{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}
.ea-myr-btn{padding:11px 17px;border-radius:11px;text-decoration:none;background:#075ee4;color:#fff!important;font-weight:750;display:inline-block}
.ea-myr-btn.secondary{background:white;color:#075ee4!important;border:1px solid #c7d9f0}
.ea-myr-empty{border:1px dashed #cbd8e9;background:#fff;border-radius:15px;padding:30px}
</style>
{% endblock %}
{% block content %}
<main class="ea-myreviews">
  <p>MY KABANKALAN JOURNEY</p><h1>My Reviews</h1>
  <p>Your ratings and experiences with Kabankalan destinations.</p>
  <nav class="ea-myr-actions"><a class="ea-myr-btn" href="{% url 'places:journey_dashboard' %}">My Journey</a><a class="ea-myr-btn secondary" href="{% url 'places:attraction_carousel' %}">Explore Places</a></nav>
  {% for review in reviews %}
    <article class="ea-myr-card"><h2>{{ review.place.title }}</h2>
      <span class="ea-myr-stars">{{ review.rating }} / 5 stars</span>
      <small> · {{ review.created_at|date:"M j, Y" }}</small>
      {% if review.comment %}<p>{{ review.comment|linebreaksbr }}</p>{% endif %}
      {% if review.place.is_active and review.place.is_verified %}
      <a class="ea-myr-btn secondary" href="{% url 'places:place_detail' review.place.pk %}#place-reviews">View / Edit Review</a>
      {% else %}<p>This destination is no longer publicly listed. Your review is retained.</p>{% endif %}
    </article>
  {% empty %}
    <section class="ea-myr-empty"><h2>No reviews submitted yet</h2><p>Explore Kabankalan places and add your first rating.</p></section>
  {% endfor %}
</main>
{% endblock %}
'''

JOURNEY_HTML = r'''
<!-- ExploreAnywhere phase3e reviews v1 -->
<section class="ea-journey-panel" aria-label="My reviews">
  <h2>My Reviews</h2>
  {% for review in my_reviews_preview %}
    {% if review.place.is_active and review.place.is_verified %}
      <a class="ea-journey-item" href="{% url 'places:place_detail' review.place.pk %}#place-reviews">{{ review.place.title }} · {{ review.rating }}/5 stars</a>
    {% else %}
      <p>{{ review.place.title }} · {{ review.rating }}/5 stars (no longer published)</p>
    {% endif %}
  {% empty %}
    <p>No reviews yet. Share your experience with a Kabankalan destination.</p>
  {% endfor %}
  <a class="ea-journey-link" href="{% url 'places:my_reviews' %}">View All Reviews</a>
</section>
'''


def fail(message):
    raise RuntimeError(message)


def read(path):
    return (ROOT / path).read_text(encoding='utf-8-sig')


def once(text, old, replacement, label):
    count = text.count(old)
    if count != 1:
        fail(f'{label}: expected one anchor, found {count}. No files changed.')
    return text.replace(old, replacement, 1)


def main():
    for path in (URLS, VIEWS, MODELS, JOURNEY_VIEWS, DETAIL, DASHBOARD):
        if not (ROOT / path).is_file():
            fail(f'Missing {path}. Run from the ExploreAnywhere Django project root.')
    for path in (REVIEW_VIEWS, MY_REVIEWS):
        if (ROOT / path).exists():
            fail(f'{path} already exists. To avoid overwriting existing work, STOPPED.')
    urls = read(URLS)
    views = read(VIEWS)
    models = read(MODELS)
    journey_views = read(JOURNEY_VIEWS)
    detail = read(DETAIL)
    dashboard = read(DASHBOARD)
    if 'class Review(' not in models or 'class Place(' not in models:
        fail('Review or Place models differ from audited schema.')
    if MARK in urls or MARK in detail or MARK in dashboard:
        fail('Phase 3E appears already installed. No changes made.')
    if 'path("saved/"' not in urls or 'path("journey/"' not in urls:
        fail('Phase 3 Saved/Journey routes missing. Run Phase 3 builder first.')
    if '"places/place_detail.html"' not in views or 'def place_detail(request, pk):' not in views:
        fail('Place details view differs from audited project.')
    if '"review_count": review_count,' not in journey_views:
        fail('Journey dashboard context changed; will not overwrite.')
    if 'class SavedPlace' not in models or '"is_saved":' not in views:
        fail('Phase 3 saved places not detected; stop rather than risking data.')

    # Add dedicated review routes; the dynamic <int:pk>/ detail route remains unchanged.
    urls = once(urls, 'from . import views, journey_views',
                'from . import views, journey_views, review_views', 'Review views import')
    urls = once(urls, '    path("saved/", journey_views.saved_places, name="saved_places"),',
                '    # ' + MARK + '\n'
                '    path("my-reviews/", review_views.my_reviews, name="my_reviews"),\n'
                '    path("<int:pk>/review/", review_views.submit_review, name="submit_review"),\n'
                '    path("<int:pk>/review/delete/", review_views.delete_review, name="delete_review"),\n'
                '    path("saved/", journey_views.saved_places, name="saved_places"),', 'Review URL routes')

    # Restrict the changes to the existing place_detail context, not the search view.
    start = views.index('def place_detail(request, pk):')
    target = '            "is_saved": SavedPlace.objects.filter(user=request.user, place=place).exists(),'
    if views[start:].count(target) != 1:
        fail('Unexpected place_detail context; no changes made.')
    views = once(views, 'from .models import Place, SavedPlace',
                 'from .models import Place, SavedPlace, Review', 'Review import')
    views = once(views, target,
                 target + '\n'
                 '            # ' + MARK + '\n'
                 '            "my_review": Review.objects.filter(user=request.user, place=place).order_by("pk").first(),\n'
                 '            "public_reviews": Review.objects.filter(place=place).select_related("user").order_by("-created_at")[:8],\n'
                 '            "review_rating_options": (5, 4, 3, 2, 1),', 'Place detail review context')

    # Extend journey preview without changing its existing counts or itinerary links.
    journey_views = once(journey_views, '        "review_count": review_count,',
                         '        "review_count": review_count,\n'
                         '        "my_reviews_preview": (Review.objects.filter(user=request.user, place__city_id=KABANKALAN_CITY_ID)\n'
                         '            .select_related("place").order_by("-created_at")[:4]),  # ' + MARK,
                         'Journey preview context')
    if detail.count('</style>') != 1 or detail.count('</main>') != 1:
        fail('Place details style/content boundaries changed; no files changed.')
    detail = once(detail, '</style>', CSS_DETAIL + '\n</style>', 'Place details style')
    detail = once(detail, '</main>', HTML_DETAIL + '\n</main>', 'Place details review panels')

    if dashboard.count('</div>\n</main>') != 1:
        fail('Journey grid closing anchor not unique; no files changed.')
    dashboard = once(dashboard, '</div>\n</main>',
                     JOURNEY_HTML + '\n</div>\n</main>', 'Journey review panel')

    modifications = {
        URLS: urls, VIEWS: views, JOURNEY_VIEWS: journey_views,
        DETAIL: detail, DASHBOARD: dashboard,
        REVIEW_VIEWS: REVIEW_CODE, MY_REVIEWS: MY_REVIEWS_HTML,
    }
    for path, content in modifications.items():
        if path.suffix == '.py':
            ast.parse(content, filename=str(path))
        if path.suffix == '.html' and ('{% block content %}' not in content or '{% endblock %}' not in content):
            fail(f'Template block markers missing: {path}')

    backup = ROOT / 'phase3_backups' / ('reviews-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=False)
    existing = {p: (ROOT / p).exists() for p in modifications}
    for p, existed in existing.items():
        if existed:
            destination = backup / p
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / p, destination)
    written = []
    try:
        for p, content in modifications.items():
            dest = ROOT / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding='utf-8', newline='\n')
            written.append(p)
    except Exception:
        for p in reversed(written):
            if existing[p]:
                shutil.copy2(backup / p, ROOT / p)
            else:
                (ROOT / p).unlink(missing_ok=True)
        raise
    print('SUCCESS: Phase 3E Reviews installed.')
    print('Added rating/comment submission, user-owned updates/deletion, and recalculated place review statistics.')
    print('Added My Reviews page and Journey dashboard review preview.')
    print('No schema changes or migrations. No existing review records were modified by installation.')
    print('Backup:', backup.relative_to(ROOT))
    print('Routes: /places/my-reviews/  /places/<id>/review/ (POST)  /places/<id>/review/delete/ (POST)')
    print('Next: python manage.py check')
    print('Next: python manage.py shell -c "from django.template.loader import get_template; [get_template(n) for n in [\'places/place_detail.html\',\'places/journey_dashboard.html\',\'places/my_reviews.html\']]; print(\'Templates OK\')"')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('STOPPED:', exc, file=sys.stderr)
        sys.exit(1)
