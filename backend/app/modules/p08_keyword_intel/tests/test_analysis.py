"""Pure analysis tests — no DB."""
import pytest

from app.modules.p08_keyword_intel.analysis import Classifier, keyword_insights, negative_candidates
from app.modules.p21_business_rules.interface import Rules

pytestmark = pytest.mark.module("P08")
CLF = Classifier(Rules(competitor_terms=["blacklane"], brand_terms=["corporate cars melbourne"]))


def term(t, cost=10.0, clicks=5, conv=0.0, camp="100", status="NONE", ag="10"):
    return {"search_term": t, "cost": cost, "clicks": clicks, "impressions": clicks * 10, "conversions": conv,
            "campaign_google_id": camp, "ad_group_google_id": ag, "status": status}


@pytest.mark.parametrize("t,intent,value", [
    ("chauffeur jobs melbourne", "excluded", "negative"),
    ("cheap airport taxi", "excluded", "negative"),
    ("sydney airport transfer", "wrong_location", "negative"),
    ("melbourne to sydney chauffeur", "service_location", "high"),  # covered area present → not wrong location
    ("blacklane melbourne", "competitor", "low"),
    ("corporate cars melbourne", "brand", "high"),
    ("airport transfer melbourne", "service_location", "high"),
    ("wedding car hire", "service", "medium"),
    ("things to do in melbourne", "location_only", "low"),
    ("xyz abc", "unclassified", "unknown"),
])
def test_classify(t, intent, value):
    got = CLF.classify(t)
    assert (got[0], got[1]) == (intent, value) and got[2]


def test_whole_word_matching_only():
    assert CLF.classify("cabernet winery tour")[0] != "excluded"  # 'cab' must not match inside 'cabernet'


def test_excluded_word_becomes_phrase_negative_with_evidence():
    out = negative_candidates([term("uber melbourne airport", 8, 4), term("uber eats driver", 5, 3)], CLF)
    c = next(c for c in out if c.text == "uber")
    assert c.match_type == "PHRASE" and c.campaign_google_id is None and c.confidence >= 0.9
    assert c.cost == 13 and c.clicks == 7 and c.term_count == 2 and "uber eats driver" in c.examples


def test_excluded_word_with_conversions_gets_low_confidence():
    out = negative_candidates([term("cheap chauffeur melbourne", 30, 10, conv=2)], CLF)
    c = next(c for c in out if c.text == "cheap")
    assert c.confidence == 0.5 and "check before adding" in c.reason


def test_costly_irrelevant_term_becomes_exact_negative():
    out = negative_candidates([term("xyz random thing", cost=40, clicks=12)], CLF)
    c = next(c for c in out if c.match_type == "EXACT")
    assert c.text == "xyz random thing" and c.campaign_google_id == "100" and c.source == "no_conversions"


def test_relevant_non_converting_term_is_not_negated():
    out = negative_candidates([term("airport transfer melbourne", cost=90, clicks=30)], CLF)
    assert not any(c.text == "airport transfer melbourne" for c in out)


def test_below_thresholds_not_negated():
    out = negative_candidates([term("xyz random thing", cost=5, clicks=1)], CLF)
    assert not out


def test_already_excluded_terms_ignored():
    assert not negative_candidates([term("uber jobs", status="EXCLUDED")], CLF)


def test_exact_candidate_dropped_when_covered_by_phrase():
    out = negative_candidates([term("free parking tullamarine", 50, 20)], CLF)
    assert [c.text for c in out if c.match_type == "EXACT"] == []
    assert {"free", "parking"} <= {c.text for c in out}


def test_pattern_words_need_three_terms_and_spend():
    rows = [term(f"zorbing option {i}", cost=15, clicks=5) for i in range(3)]
    texts = {c.text for c in negative_candidates(rows, CLF)}
    assert "zorbing" in texts and "option" in texts


def test_keyword_insights_buckets():
    kws = [
        {"text": "airport transfer", "match_type": "PHRASE", "status": "ENABLED", "quality_score": 3, "impressions": 100,
         "clicks": 10, "cost": 50, "conversions": 0, "cost_per_conversion": None, "ad_group_name": "A"},
        {"text": "airport transfer", "match_type": "PHRASE", "status": "ENABLED", "quality_score": 8, "impressions": 0,
         "clicks": 0, "cost": 0, "conversions": 0, "cost_per_conversion": None, "ad_group_name": "B"},
        {"text": "chauffeur melbourne", "match_type": "EXACT", "status": "ENABLED", "quality_score": 9, "impressions": 50,
         "clicks": 5, "cost": 20, "conversions": 2, "cost_per_conversion": 10, "ad_group_name": "A"},
    ]
    terms = [term("luxury car hire melbourne", cost=12, clicks=3, conv=1), term("uber melbourne", conv=1)]
    ins = keyword_insights(kws, terms, CLF)
    assert [k["ad_group_name"] for k in ins["wasters"]] == ["A"]
    assert ins["winners"][0]["text"] == "chauffeur melbourne"
    assert ins["low_quality_score"][0]["quality_score"] == 3
    assert ins["idle"][0]["ad_group_name"] == "B"
    assert "2 ad groups" in ins["duplicates"][0]["reason"]
    assert [t["search_term"] for t in ins["expansion_candidates"]] == ["luxury car hire melbourne"]  # uber excluded


def test_target_cpa_flags_expensive_winners():
    clf = Classifier(Rules(target_cost_per_conversion=5))
    kws = [{"text": "x", "match_type": "EXACT", "status": "ENABLED", "quality_score": 7, "impressions": 5, "clicks": 5,
            "cost": 20, "conversions": 2, "cost_per_conversion": 10, "ad_group_name": "A"}]
    assert "above your target" in keyword_insights(kws, [], clf)["winners"][0]["reason"]


def test_excluded_word_also_in_service_searches_is_downgraded():
    out = negative_candidates([term("rent a car with a chauffeur", 5, 2)], CLF)
    c = next(c for c in out if c.text == "rent a car")
    assert c.confidence == 0.6 and "also mention your services" in c.reason


def test_idle_and_duplicates_ignore_paused_campaigns():
    kws = [{"text": "a", "match_type": "EXACT", "status": "ENABLED", "quality_score": 7, "impressions": 0, "clicks": 0,
            "cost": 0, "conversions": 0, "cost_per_conversion": None, "ad_group_name": g, "campaign_google_id": c}
           for g, c in [("A", "1"), ("B", "1"), ("C", "2")]]
    ins = keyword_insights(kws, [], CLF, enabled_campaigns={"1"})
    assert len(ins["idle"]) == 2 and len(ins["duplicates"]) == 1 and "2 ad groups" in ins["duplicates"][0]["reason"]
    assert keyword_insights(kws, [], CLF, enabled_campaigns=set())["idle"] == []


def test_single_word_intent_negative_not_downgraded_by_service_word():
    c = next(c for c in negative_candidates([term("chauffeur jobs melbourne")], CLF) if c.text == "jobs")
    assert c.confidence == 0.95
