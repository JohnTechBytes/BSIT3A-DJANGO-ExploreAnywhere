"""The public usability evaluation pages.

A visitor answers the ten System Usability Scale items; the score is computed
with the standard SUS formula that ships with the ``SusResponse`` model and
the result is shown on the thank-you page.
"""
from django.shortcuts import redirect, render

from apps.info.models import SusResponse

from .forms import SusForm

# The widely used SUS interpretation bands (Sauro & Lewis).
SCORE_BANDS = (
    (85.0, "Excellent", "The system is easy to use and the tasks felt natural."),
    (72.7, "Good", "The system works well and most tasks felt straightforward."),
    (62.7, "OK", "The system is usable, with a few rough edges around the edges."),
    (51.0, "Poor", "Several tasks were confusing and the system needs work."),
    (0.0, "Awful", "The system was hard to use and most tasks failed."),
)


def score_band(response):
    """Return the (label, explanation) band for a scored response."""
    if response is None:
        return None
    score = float(response.score)
    for threshold, label, explanation in SCORE_BANDS:
        if score >= threshold:
            return {"label": label, "explanation": explanation, "score": score}
    return {"label": "Awful", "explanation": SCORE_BANDS[-1][2], "score": score}


def current_response(request):
    """The response of this browser session or signed-in account."""
    pk = request.session.get("sus_response_id")
    if pk:
        response = SusResponse.objects.filter(pk=pk).first()
        if response is not None:
            return response
    if request.user.is_authenticated:
        return (
            SusResponse.objects.filter(user=request.user)
            .order_by("-created_at", "-pk")
            .first()
        )
    return None


def sus_survey(request):
    """Answer the ten SUS items."""
    form = SusForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = request.user if request.user.is_authenticated else None
        response = form.response(user=user)
        response.save()
        request.session["sus_response_id"] = response.pk
        return redirect("evaluation:sus_thanks")

    previous = current_response(request)
    return render(
        request,
        "evaluation/sus_form.html",
        {
            "form": form,
            "previous": previous,
            "previous_band": score_band(previous),
        },
    )


def answered_items(response):
    """The ten answers with their wording, for the result page."""
    if response is None:
        return []
    items = []
    for index in range(1, 11):
        name = f"q{index}"
        items.append({
            "label": SusResponse._meta.get_field(name).help_text,
            "value": getattr(response, name),
        })
    return items


def sus_thanks(request):
    """Show the score of the response that was just submitted."""
    response = current_response(request)
    return render(
        request,
        "evaluation/thank_you.html",
        {
            "response": response,
            "band": score_band(response),
            "answers": answered_items(response),
        },
    )
