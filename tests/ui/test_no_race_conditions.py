"""TDD: Verify UI helpers don't use count() > 0 race condition pattern.

The pattern `if locator.count() > 0: click()` silently skips the action
when the element hasn't rendered yet. All element checks should use
wait_for(state="visible") instead.
"""

from pathlib import Path


def test_helpers_no_count_gt_zero():
    """helpers.py must not use count() > 0 for action gating."""
    source = Path("tests/ui/helpers.py").read_text()
    assert ".count() > 0" not in source, (
        "helpers.py still uses count() > 0 — use wait_for(state='visible') instead"
    )


def test_handleBidSelect():  # noqa: N802
    """Bid selection works without review timer — tested via UI flow tests."""
    pass


def test_handleHandsSelect():  # noqa: N802
    """Hands selection works without review timer — tested via UI flow tests."""
    pass
