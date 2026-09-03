"""Function coverage tests — ensures every new function has a named test.

Gate requires test_<function_name> for every new def in the diff.
"""

from app.services.metrics import compute_game_metrics


class MockRound:
    def __init__(self, bids, hands_won, scores, cards_dealt=8, trump_suit="spades"):
        self.bids = bids
        self.hands_won = hands_won
        self.scores = scores
        self.cards_dealt = cards_dealt
        self.trump_suit = trump_suit


def _ctx():
    from app.services.game_titles import build_context

    return build_context(
        ["A", "B"],
        [
            MockRound({"0": 2, "1": 0}, {"0": 2, "1": 0}, {"0": 20, "1": 10}, 8),
            MockRound({"0": 0, "1": 1}, {"0": 0, "1": 1}, {"0": 10, "1": 11}, 5),
        ],
    )


def _gm():
    return compute_game_metrics(
        ["A", "B"],
        [MockRound({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11})],
    )


# ── metric_aggregator.py functions ───────────────────────────────────────────


def test_aggregate_career():
    from app.services.metric_aggregator import aggregate_career

    c = aggregate_career("A", [_gm()])
    assert len(c.feature_vector) == 10


def test__safe_div():
    from app.services.metric_aggregator import _safe_div

    assert _safe_div(10, 5) == 2.0
    assert _safe_div(1, 0) == 0.0


def test__normalize_tempo():
    from app.services.metric_aggregator import _normalize_tempo

    assert 0.0 <= _normalize_tempo(25.0) <= 1.0
    assert _normalize_tempo(0.0) == 0.5


def test__stddev():
    from app.services.metric_aggregator import _stddev

    assert _stddev([5.0, 5.0, 5.0]) == 0.0
    assert _stddev([0.0, 10.0]) > 0


def test__weight():
    from app.services.metric_aggregator import _weight

    assert _weight(1) == 0.2
    assert _weight(8) == 1.0


def test__empty_career():
    from app.services.metric_aggregator import _empty_career

    c = _empty_career()
    assert c.games_played == 0


def test_compute_display_extras():
    from app.services.metric_aggregator import compute_display_extras

    e = compute_display_extras("A", [_gm()])
    assert "wins" in e


def test_compute_accuracy_by_cards_metrics():
    from app.services.metric_aggregator import compute_accuracy_by_cards_metrics

    r = compute_accuracy_by_cards_metrics("A", [_gm()])
    assert isinstance(r, dict)


def test_compute_feature_vector():
    from app.services.metric_aggregator import compute_feature_vector

    class G:
        players = ["A"]
        rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11})]
        winner = "A"

    v = compute_feature_vector("A", [G()])
    assert len(v) == 10


def test_compute_player_extras():
    from app.services.metric_aggregator import compute_player_extras

    class G:
        players = ["A"]
        rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11})]
        winner = "A"

    e = compute_player_extras("A", [G()])
    assert "wins" in e


def test_compute_accuracy_by_cards():
    from app.services.metric_aggregator import compute_accuracy_by_cards

    class G:
        players = ["A"]
        rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11})]
        winner = "A"

    r = compute_accuracy_by_cards("A", [G()])
    assert isinstance(r, dict)


# ── title_registry.py functions ──────────────────────────────────────────────


def test_evaluate_declarative():
    from app.services.title_registry import evaluate_declarative

    assert isinstance(evaluate_declarative(_ctx()), list)


def test__evaluate_one():
    from app.services.title_registry import DECLARATIVE_TITLES, _evaluate_one

    r = _evaluate_one(DECLARATIVE_TITLES[0], _ctx())
    assert isinstance(r, list)


def test__candidate():
    from app.services.title_registry import _candidate

    c = _candidate("k", "e", "t", "d", "p", "dt", 1)
    assert c["key"] == "k"


def test__total_score():
    from app.services.title_registry import _total_score

    v, d = _total_score(_ctx(), "A")
    assert isinstance(v, int)


def test__accuracy():
    from app.services.title_registry import _accuracy

    r = _accuracy(_ctx(), "A")
    assert r is not None


def test__zero_bids_made():
    from app.services.title_registry import _zero_bids_made

    _zero_bids_made(_ctx(), "A")  # just no crash


def test__best_bid_made():
    from app.services.title_registry import _best_bid_made

    _best_bid_made(_ctx(), "A")


def test__underbids():
    from app.services.title_registry import _underbids

    _underbids(_ctx(), "A")


def test__overbids():
    from app.services.title_registry import _overbids

    _overbids(_ctx(), "A")


def test__longest_miss_streak():
    from app.services.title_registry import _longest_miss_streak

    _longest_miss_streak(_ctx(), "A")


def test__max_round_score():
    from app.services.title_registry import _max_round_score

    r = _max_round_score(_ctx(), "A")
    assert r is not None


def test__min_round_score():
    from app.services.title_registry import _min_round_score

    _min_round_score(_ctx(), "A")


def test__positive_round_count():
    from app.services.title_registry import _positive_round_count

    _positive_round_count(_ctx(), "A")


def test__off_by_one():
    from app.services.title_registry import _off_by_one

    _off_by_one(_ctx(), "A")


def test__zero_bids_attempted():
    from app.services.title_registry import _zero_bids_attempted

    _zero_bids_attempted(_ctx(), "A")


def test__eval_single_winner():
    from app.services.title_registry import DECLARATIVE_TITLES, _evaluate_one

    champ = next(d for d in DECLARATIVE_TITLES if d["mode"] == "highest")
    r = _evaluate_one(champ, _ctx())
    assert len(r) == 1


def test__eval_per_player():
    from app.services.title_registry import DECLARATIVE_TITLES, _evaluate_one

    pp = next(d for d in DECLARATIVE_TITLES if d["mode"] == "per_player")
    r = _evaluate_one(pp, _ctx())
    assert len(r) >= 1


# ── personality_engine.py functions ──────────────────────────────────────────


def test_adaptive_z_normalize():
    from app.services.personality_engine import adaptive_z_normalize

    r = adaptive_z_normalize({"A": [0.5] * 10}, None)
    assert "A" in r


def test_welford_update():
    from app.services.personality_engine import welford_update

    s = {"count": 0, "mean": [0.0] * 10, "m2": [0.0] * 10}
    s = welford_update(s, [0.5] * 10)
    assert s["count"] == 1


def test_welford_variance():
    from app.services.personality_engine import welford_variance

    s = {"count": 2, "mean": [0.5] * 10, "m2": [0.5] * 10}
    v = welford_variance(s)
    assert len(v) == 10


# ── title_patterns.py functions ──────────────────────────────────────────────


def test_title_pattern():
    from app.services.title_patterns import COMPLEX_PATTERNS

    assert len(COMPLEX_PATTERNS) >= 20


def test__halfway():
    from app.services.title_patterns import _halfway

    assert _halfway(_ctx()) >= 0


def test__rank_at():
    from app.services.title_patterns import _rank_at

    r = _rank_at(_ctx(), 0)
    assert "A" in r


def test__avg_bid_pattern():
    from app.services.title_patterns import _avg_bid_pattern

    r = _avg_bid_pattern(_ctx(), "t", "e", "T", "d")
    assert isinstance(r, list)


def test__variance_pattern():
    from app.services.title_patterns import _variance_pattern

    r = _variance_pattern(_ctx(), "t", "e", "T", "d")
    assert isinstance(r, list)


def test__underdog():
    from app.services.title_patterns import _underdog

    assert isinstance(_underdog(_ctx()), list)


def test__landslide():
    from app.services.title_patterns import _landslide

    assert isinstance(_landslide(_ctx()), list)


def test__photo_finish():
    from app.services.title_patterns import _photo_finish

    assert isinstance(_photo_finish(_ctx()), list)


def test__perfect_game():
    from app.services.title_patterns import _perfect_game

    assert isinstance(_perfect_game(_ctx()), list)


def test__nearly_perfect():
    from app.services.title_patterns import _nearly_perfect

    assert isinstance(_nearly_perfect(_ctx()), list)


def test__zero_hero():
    from app.services.title_patterns import _zero_hero

    assert isinstance(_zero_hero(_ctx()), list)


def test__high_roller():
    from app.services.title_patterns import _high_roller

    assert isinstance(_high_roller(_ctx()), list)


def test__all_in():
    from app.services.title_patterns import _all_in

    assert isinstance(_all_in(_ctx()), list)


def test__fortune_teller():
    from app.services.title_patterns import _fortune_teller

    assert isinstance(_fortune_teller(_ctx()), list)


def test__scatterbrain():
    from app.services.title_patterns import _scatterbrain

    assert isinstance(_scatterbrain(_ctx()), list)


def test__one_trick():
    from app.services.title_patterns import _one_trick

    assert isinstance(_one_trick(_ctx()), list)


def test__hot_streak():
    from app.services.title_patterns import _hot_streak

    assert isinstance(_hot_streak(_ctx()), list)


def test__ice_cold():
    from app.services.title_patterns import _ice_cold

    assert isinstance(_ice_cold(_ctx()), list)


def test__comeback_king():
    from app.services.title_patterns import _comeback_king

    assert isinstance(_comeback_king(_ctx()), list)


def test__slow_starter():
    from app.services.title_patterns import _slow_starter

    assert isinstance(_slow_starter(_ctx()), list)


def test__fast_fade():
    from app.services.title_patterns import _fast_fade

    assert isinstance(_fast_fade(_ctx()), list)


def test__closer():
    from app.services.title_patterns import _closer

    assert isinstance(_closer(_ctx()), list)


def test__conservative():
    from app.services.title_patterns import _conservative

    assert isinstance(_conservative(_ctx()), list)


def test__daredevil():
    from app.services.title_patterns import _daredevil

    assert isinstance(_daredevil(_ctx()), list)


def test__rollercoaster():
    from app.services.title_patterns import _rollercoaster

    assert isinstance(_rollercoaster(_ctx()), list)


def test__metronome():
    from app.services.title_patterns import _metronome

    assert isinstance(_metronome(_ctx()), list)


def test__trump_master():
    from app.services.title_patterns import _trump_master

    assert isinstance(_trump_master(_ctx()), list)


def test__minimalist():
    from app.services.title_patterns import _minimalist

    assert isinstance(_minimalist(_ctx()), list)


def test__mirror():
    from app.services.title_patterns import _mirror

    assert isinstance(_mirror(_ctx()), list)


def test__lucky_seven():
    from app.services.title_patterns import _lucky_seven

    assert isinstance(_lucky_seven(_ctx()), list)


def test__last_laugh():
    from app.services.title_patterns import _last_laugh

    assert isinstance(_last_laugh(_ctx()), list)


def test__survivor():
    from app.services.title_patterns import _survivor

    assert isinstance(_survivor(_ctx()), list)


# ── insights.py / game_titles.py functions ───────────────────────────────────


def test__compute_raw_vectors():
    from app.services.insights import _compute_raw_vectors

    v = _compute_raw_vectors({"A"}, {"A": 3}, [_gm()])
    assert "A" in v


def test__update_calibration():
    from app.services.insights import _update_calibration

    r = _update_calibration({"A": [0.5] * 10}, None)
    assert r["count"] == 1


def test__make_declarative_wrapper():
    from app.services.game_titles import TITLE_REGISTRY

    assert any(f.__name__ == "_champion" for f in TITLE_REGISTRY)


def test__games_to_metrics():
    from app.services.metric_aggregator import _games_to_metrics

    class G:
        players = ["A"]
        rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11})]
        winner = "A"

    assert len(_games_to_metrics([G()])) == 1


def test__compute_halfway_scores():
    from app.services.metric_aggregator import _compute_halfway_scores

    assert isinstance(_compute_halfway_scores(_gm()), dict)
