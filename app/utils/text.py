"""Safe display helpers for user-authored text."""

import re

from markupsafe import Markup, escape

_LINK_PATTERN = re.compile(
    r"(?P<url>(?:https?://|www\.)[^\s<>]+)|"
    r"(?P<email>[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
    re.IGNORECASE,
)
_TRAILING_PUNCTUATION = ".,;:!?"


def linkify_text(value: object | None) -> Markup:
    """Escape user text and turn URLs and email addresses into safe links."""
    if value is None:
        return Markup("")

    source = str(value)
    rendered: list[Markup] = []
    cursor = 0
    for match in _LINK_PATTERN.finditer(source):
        rendered.append(escape(source[cursor : match.start()]))
        label = match.group(0)
        linked_label = label.rstrip(_TRAILING_PUNCTUATION)
        trailing = label[len(linked_label) :]
        if match.lastgroup == "email":
            href = f"mailto:{linked_label}"
            attributes = ""
        else:
            href = (
                linked_label
                if linked_label.lower().startswith(("http://", "https://"))
                else f"https://{linked_label}"
            )
            attributes = ' rel="noopener noreferrer"'
        rendered.append(
            Markup('<a href="{}"{}>{}</a>').format(
                escape(href), Markup(attributes), escape(linked_label)
            )
        )
        rendered.append(escape(trailing))
        cursor = match.end()
    rendered.append(escape(source[cursor:]))
    return Markup("").join(rendered)
