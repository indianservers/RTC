import pytest
from app.nlp.constraints import constraints


@pytest.mark.parametrize(
    "text,want",
    [
        ("No AC buses.", {"ac": False}),
        ("Only non-AC.", {"ac": False}),
        ("Not a sleeper.", {"sleeper": False}),
        ("Only AC.", {"ac": True}),
        ("Only sleeper.", {"sleeper": True}),
        ("Non AC seater.", {"ac": False, "sleeper": False}),
        ("with AC and not a sleeper", {"ac": True, "sleeper": False}),
    ],
)
def test_constraints(text, want):
    assert constraints(text) == want


@pytest.mark.parametrize("text", ["only ac and non-ac", "only sleeper not a sleeper"])
def test_conflicts(text):
    with pytest.raises(ValueError):
        constraints(text)
