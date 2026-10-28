"""The ONE rule engine. The gateway uses it live; the verifier replays it over ground truth."""
from dataclasses import dataclass, field
import operator

OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt, "==": operator.eq}


@dataclass
class Decision:
    allowed: bool
    rule: str = "OK"
    reason: str = ""
    needs_approval: bool = False
    skip: bool = False


@dataclass
class RunState:
    counts: dict = field(default_factory=dict)
    facts: dict = field(default_factory=dict)


class Policy:
    def __init__(self, contract):
        self.c = contract

    def check(self, system, action, args, state, ctx, ledger) -> Decision:
        full = f"{system}.{action}"
        perm = self.c.permissions.get(system)
        if perm is None:
            return Decision(False, "UNDECLARED_SYSTEM", f"'{system}' is not in the contract")
        if action in perm.deny:
            return Decision(False, "DENIED", f"{full} is explicitly denied")
        if action not in perm.read and action not in perm.write:
            return Decision(False, "UNDECLARED_ACTION", f"{full} is not declared")
        for k, v in perm.scope.items():
            if args.get(k) != v:
                return Decision(False, "SCOPE", f"{full} must have {k}={v!r}, got {args.get(k)!r}")

        se = self.c.side_effects.get(full)
        if se is None:                       # a declared read: no further limits
            return Decision(True)

        if se.condition:
            c = se.condition
            if c["fact"] not in state.facts:
                return Decision(False, "CONDITION", f"fact '{c['fact']}' was never measured")
            if not OPS[c["op"]](state.facts[c["fact"]], c["value"]):
                return Decision(False, "CONDITION",
                                f"{c['fact']}={state.facts[c['fact']]:.2f} fails {c['op']} {c['value']}")
        if se.max_per_run is not None and state.counts.get(full, 0) >= se.max_per_run:
            return Decision(False, "BUDGET", f"{full} limited to {se.max_per_run} per run")
        if se.replay_key and (full, ctx.get(se.replay_key)) in ledger and se.on_replay == "skip":
            return Decision(True, "REPLAY_SKIP", "already done for this key", skip=True)
        return Decision(True, needs_approval=se.requires_approval)

    def commit(self, system, action, state, ctx, ledger):
        full = f"{system}.{action}"
        state.counts[full] = state.counts.get(full, 0) + 1
        se = self.c.side_effects.get(full)
        if se and se.replay_key:
            ledger.add((full, ctx.get(se.replay_key)))

    def observe(self, system, action, result, state):
        full = f"{system}.{action}"
        for f in self.c.facts:
            if f["from_action"] == full and isinstance(result, dict):
                state.facts[f["name"]] = result.get(f["result_key"])
