import pytest
from contractguard.contract import Contract, ContractError
from contractguard.scenarios import scenarios, rules_seen
from contractguard import agents as A
from contractguard.harness import run
from contractguard.scenarios import DUP

CASES = scenarios()


@pytest.mark.parametrize("name,fn,verdict,rules", CASES, ids=[c[0] for c in CASES])
def test_scenario(name, fn, verdict, rules):
    r = fn()
    assert r.verdict == verdict, r.findings
    assert rules <= rules_seen(r)


# --- ground truth checks: look at the WORLD, not at what the agent says ---
def test_issue_really_stays_open_when_agent_tries_to_close():
    r = run(DUP, A.overreach_close)
    assert r.world.issues[2]["open"] is True
    assert len(r.world.comments) == 1             # the allowed action still worked


def test_replay_never_comments_twice():
    r = run(DUP, A.compliant, runs=2)
    assert len(r.world.comments) == 1
    assert len(r.world.collections["issues"]) == 2   # upsert overwrote, no duplicates


def test_no_slack_message_leaves_the_building():
    assert run(DUP, A.undeclared_system).world.slack_msgs == []


def test_prod_collection_untouched():
    r = run(DUP, A.wrong_scope)
    assert list(r.world.collections["prod_customers"]) == [101]


def test_bypass_does_hurt_without_gateway():
    r = run(DUP, A.bypasser)
    assert r.world.issues[2]["open"] is False      # damage done: only DETECTED, not prevented


# --- the contract file itself is linted ---
def test_lint_rejects_write_without_side_effect():
    raw = dict(Contract.load("contracts/duplicate-issue-detector.yaml").raw)
    raw["side_effects"] = raw["side_effects"][:1]  # drop the upsert declaration
    with pytest.raises(ContractError, match="no declared side_effect"):
        Contract.from_dict(raw)


def test_lint_rejects_missing_field():
    raw = dict(Contract.load("contracts/duplicate-issue-detector.yaml").raw)
    del raw["replay_semantics"]
    with pytest.raises(ContractError, match="replay_semantics"):
        Contract.from_dict(raw)
