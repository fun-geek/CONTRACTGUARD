# contractguard — a test bench for agent contracts

Question it answers: **does an agent really stay inside its declared contract?**

```
python3 -m contractguard.report     # run 13 scenarios, print a table
python3 -m pytest -q                # 20 tests
```

## Architecture
```
 agent ──▶ Gateway (enforce | monitor) ──▶ World (fake GitHub/OpenAI/Qdrant/Slack)
              │  Policy (the rules)               │
              ▼                                   ▼
        audit log                      GROUND-TRUTH log (written by the systems)
                                                  │
                          Verifier replays the same Policy over it ──▶ findings
```
* `contract.py`  – loads contract.yaml and **lints** it (a write permission without a declared side effect = error)
* `policy.py`    – one rule engine: DENIED, UNDECLARED_*, SCOPE, CONDITION, BUDGET, REPLAY_SKIP, approval
* `gateway.py`   – every tool call passes here; blocks (enforce) or only logs (monitor)
* `world.py`     – mock systems that keep an honest log the agent cannot edit
* `verify.py`    – independent judge: BYPASS, SILENT_FAILURE, UNAUDITED_EFFECT, plus every policy rule on real effects
* `agents.py`    – 1 compliant agent + 9 misbehaving ones
* `scenarios.py` – expectations, including **negative controls** (cases that MUST be flagged)

## Test your own agent
Write `def my_agent(ctx, gw, world)` that only calls `gw.call(system, action, **args)`,
then `run(contract, my_agent)`. An LLM agent just maps its tool calls onto `gw.call`.
