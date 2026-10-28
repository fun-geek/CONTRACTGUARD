from .scenarios import scenarios, rules_seen


def main():
    print(f"{'scenario':32} {'verdict':9} {'expected':9} rules fired")
    print("-" * 90)
    bad = 0
    for name, fn, exp_verdict, exp_rules in scenarios():
        r = fn()
        ok = r.verdict == exp_verdict and exp_rules <= rules_seen(r)
        bad += not ok
        print(f"{name:32} {r.verdict:9} {exp_verdict:9} {sorted(rules_seen(r)) or '-'}  {'OK' if ok else '<<< UNEXPECTED'}")
    print("-" * 90)
    print("harness self-check:", "all scenarios behaved as expected" if not bad else f"{bad} unexpected result(s)")
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
