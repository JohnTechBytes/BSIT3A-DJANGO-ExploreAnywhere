
from django import template

register = template.Library()

# Illustrative travel stock photos.
# These are not claimed to depict the actual attraction.
STOCK_PHOTOS = {
    "beach": (
        "https://images.unsplash.com/"
        "photo-1507525428034-b723cf961d3e"
        "?auto=format&fit=crop&w=1000&q=80"
    ),
    "mountain": (
        "https://images.unsplash.com/"
        "photo-1464822759023-fed622ff2c3b"
        "?auto=format&fit=crop&w=1000&q=80"
    ),
    "nature": (
        "https://images.unsplash.com/"
        "photo-1441974231531-c6227db76b6e"
        "?auto=format&fit=crop&w=1000&q=80"
    ),
    "park": (
        "https://images.unsplash.com/"
        "photo-1519331379826-f10be5486c6f"
        "?auto=format&fit=crop&w=1000&q=80"
    ),
    "historic": (
        "https://images.unsplash.com/"
        "photo-1494526585095-c41746248156"
        "?auto=format&fit=crop&w=1000&q=80"
    ),
    "city": (
        "https://images.unsplash.com/"
        "photo-1480714378408-67cf0d13bc1b"
        "?auto=format&fit=crop&w=1000&q=80"
    ),
    "default": (
        "https://images.unsplash.com/"
        "photo-1500534623283-312aade485b7"
        "?auto=format&fit=crop&w=1000&q=80"
    ),
}


@register.simple_tag
def sample_photo(place):
    title = str(getattr(place, "title", "") or "").lower()

    category = getattr(place, "category", None)
    category_name = (
        str(getattr(category, "name", "") or "").lower()
        if category else ""
    )

    text = f"{title} {category_name}"

    if any(word in text for word in (
        "beach", "island", "coast", "seaside", "shore"
    )):
        return STOCK_PHOTOS["beach"]

    if any(word in text for word in (
        "mountain", "mount", "peak", "hill", "volcano"
    )):
        return STOCK_PHOTOS["mountain"]

    if any(word in text for word in (
        "waterfall", "falls", "forest", "river",
        "cave", "spring", "lake", "nature"
    )):
        return STOCK_PHOTOS["nature"]

    if any(word in text for word in (
        "park", "garden", "reserve"
    )):
        return STOCK_PHOTOS["park"]

    if any(word in text for word in (
        "museum", "heritage", "church",
        "historical", "historic", "monument"
    )):
        return STOCK_PHOTOS["historic"]

    if any(word in text for word in (
        "city", "plaza", "urban"
    )):
        return STOCK_PHOTOS["city"]

    return STOCK_PHOTOS["default"]
