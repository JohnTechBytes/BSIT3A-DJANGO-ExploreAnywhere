"""Rewards are derived from staff-approved unique destinations, never self-reports."""
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
