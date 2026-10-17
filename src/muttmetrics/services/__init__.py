"""Domain services shared by the API and the command-line tools.

Code here takes a SQLAlchemy Session and plain values, and raises plain
exceptions (LookupError, ValueError). It knows nothing about HTTP, so a CLI can
call it as easily as a route can. Anything under ``muttmetrics.api`` may import
from here; nothing outside ``muttmetrics.api`` may import from ``muttmetrics.api``
(``tests/unit/test_layering.py`` enforces it).
"""
