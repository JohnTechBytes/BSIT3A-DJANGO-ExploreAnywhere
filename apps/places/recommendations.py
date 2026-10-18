def rank_kabankalan_places(places, selected_hobbies):
    """
    Rank places using available recommendation signals.

    Hobby = 60% weight
    Rating = 20% weight when reviews exist
    Distance = reserved for real visitor GPS coordinates

    Missing rating and distance are excluded from
    the denominator, not treated as zero.
    """
    selected = set(selected_hobbies or [])
    ranked = []

    for place in places:
        place_hobbies = {
            hobby.slug for hobby in place.hobbies.all()
        }

        matching = selected.intersection(place_hobbies)

        hobby_score = (
            len(matching) / len(selected)
            if selected else 0
        )

        total = 0.60 * hobby_score
        available_weight = 0.60

        if place.review_count > 0 and place.avg_rating:
            rating_score = min(
                max(float(place.avg_rating) / 5.0, 0),
                1,
            )
            total += 0.20 * rating_score
            available_weight += 0.20

        place.match_percent = round(
            (total / available_weight) * 100
        )

        place.matched_hobbies = sorted(matching)
        place.has_hobby_match = bool(matching)

        ranked.append(place)

    ranked.sort(
        key=lambda place: (
            -place.match_percent,
            -len(place.matched_hobbies),
            place.title.lower(),
        )
    )

    return ranked
