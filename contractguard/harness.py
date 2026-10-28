from dataclasses import dataclass
from .gateway import Gateway, GuardrailViolation, ToolFailure
from .verify import verify
from .world import World


@dataclass
class Result:
    world: World
    gateways: dict
    reports: dict
    findings: list

    @property
    def blocked_rules(self):
        return [a["rule"] for g in self.gateways.values() for a in g.audit if a["outcome"] == "blocked"]

    @property
    def skipped(self):
        return [a for g in self.gateways.values() for a in g.audit if a["outcome"] == "skipped"]

    @property
    def verdict(self):
        return "HELD" if not self.findings else "BREACHED"


def run(contract, agent, issue=2, mode="enforce", runs=1, down=(), approver=None):
    world, ledger = World(), set()
    world.down = set(down)
    ctxs, gws, reps = {}, {}, {}
    for i in range(runs):
        rid = f"run{i + 1}"
        world.run_id = rid
        ctxs[rid] = {"issue_number": issue, "run_id": rid}
        gws[rid] = Gateway(contract, world, ctxs[rid], ledger, approver, mode)
        try:
            reps[rid] = agent(ctxs[rid], gws[rid], world)
        except (GuardrailViolation, ToolFailure) as e:
            reps[rid] = {"status": "failed", "error": str(e)}
    return Result(world, gws, reps, verify(contract, world, ctxs, gws, reps))
