"""Load a contract.yaml and lint it (is the contract itself coherent?)."""
from dataclasses import dataclass, field
import yaml

REQUIRED = ["inputs", "outputs", "permissions", "side_effects", "approval_points",
            "recovery_strategy", "replay_semantics", "dependencies", "state", "observability"]


class ContractError(Exception):
    pass


@dataclass
class Perm:
    read: list = field(default_factory=list)
    write: list = field(default_factory=list)
    deny: list = field(default_factory=list)
    scope: dict = field(default_factory=dict)


@dataclass
class SideEffect:
    id: str
    action: str                      # "system.action"
    max_per_run: int | None = None
    requires_approval: bool = False
    on_replay: str = "allow"         # allow | skip
    replay_key: str | None = None
    condition: dict | None = None


@dataclass
class Contract:
    workflow: str
    permissions: dict
    side_effects: dict               # full action -> SideEffect
    facts: list
    approval_points: list
    recovery_mode: str
    raw: dict

    @classmethod
    def load(cls, path):
        with open(path) as f:
            raw = yaml.safe_load(f)
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw):
        problems = []
        for k in REQUIRED:
            if k not in raw:
                problems.append(f"missing required field: {k}")
        if problems:
            raise ContractError("; ".join(problems))

        perms = {s: Perm(**{k: v for k, v in p.items()}) for s, p in raw["permissions"].items()}
        ses = {}
        for se in raw["side_effects"]:
            ses[se["action"]] = SideEffect(**se)

        # --- lint: cross-field consistency (this is what a README can never check) ---
        written = {f"{s}.{a}" for s, p in perms.items() for a in p.write}
        for w in sorted(written - set(ses)):
            problems.append(f"write permission '{w}' has no declared side_effect")
        for a in sorted(set(ses) - written):
            problems.append(f"side_effect '{a}' has no matching write permission")
        for s, p in perms.items():
            both = set(p.deny) & (set(p.read) | set(p.write))
            if both:
                problems.append(f"{s}: actions both allowed and denied: {sorted(both)}")
        need_appr = {a for a, se in ses.items() if se.requires_approval}
        if need_appr != set(raw["approval_points"]):
            problems.append(f"approval_points {sorted(raw['approval_points'])} "
                            f"!= side effects requiring approval {sorted(need_appr)}")
        if problems:
            raise ContractError("; ".join(problems))

        rs = raw["recovery_strategy"]
        mode = rs["mode"] if isinstance(rs, dict) else "fail_loud"
        return cls(raw["workflow"], perms, ses, raw.get("facts", []),
                   raw["approval_points"], mode, raw)
