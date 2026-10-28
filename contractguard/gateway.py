"""Every tool call goes through here. enforce = block; monitor = log but allow."""
from .policy import Policy, RunState


class GuardrailViolation(Exception):
    def __init__(self, decision):
        super().__init__(f"{decision.rule}: {decision.reason}")
        self.decision = decision


class ToolFailure(Exception):
    pass


class Gateway:
    def __init__(self, contract, world, ctx, ledger, approver=None, mode="enforce"):
        self.policy, self.world, self.ctx = Policy(contract), world, ctx
        self.ledger, self.approver, self.mode = ledger, approver, mode
        self.state = RunState()
        self.audit, self.executed, self.failures = [], [], []

    def _log(self, system, action, args, outcome, rule="OK", reason=""):
        short = {k: (f"<vector len={len(v)}>" if isinstance(v, list) else v) for k, v in args.items()}
        self.audit.append(dict(seq=len(self.audit) + 1, call=f"{system}.{action}",
                               args=short, outcome=outcome, rule=rule, reason=reason))

    def call(self, system, action, **args):
        d = self.policy.check(system, action, args, self.state, self.ctx, self.ledger)

        if not d.allowed:
            if self.mode == "enforce":
                self._log(system, action, args, "blocked", d.rule, d.reason)
                raise GuardrailViolation(d)
            self._log(system, action, args, "VIOLATION_ALLOWED(monitor)", d.rule, d.reason)
        elif d.skip:
            self._log(system, action, args, "skipped", d.rule, d.reason)
            return {"skipped": True, "reason": d.reason}
        elif d.needs_approval:
            ok = bool(self.approver and self.approver(f"{system}.{action}", args))
            if not ok:
                d.rule, d.reason = "APPROVAL_DENIED", "human did not approve"
                self._log(system, action, args, "blocked", d.rule, d.reason)
                raise GuardrailViolation(d)
            self._log(system, action, args, "approved")

        try:
            result = self.world.dispatch(system, action, args)
        except Exception as e:                       # tool/dependency failure
            self.failures.append(f"{system}.{action}: {e}")
            self._log(system, action, args, "tool_failed", "RECOVERY", str(e))
            raise ToolFailure(str(e)) from e

        self.executed.append(f"{system}.{action}")
        self.policy.commit(system, action, self.state, self.ctx, self.ledger)
        self.policy.observe(system, action, result, self.state)
        if d.allowed and not d.needs_approval:
            self._log(system, action, args, "allowed")
        return result
