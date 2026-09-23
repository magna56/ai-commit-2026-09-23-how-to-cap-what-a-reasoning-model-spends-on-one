"""Pick a reasoning-token cap from your own logs, not from a round number.

Every major API replaced the thinking-token BUDGET with an effort LEVEL. A
level shifts the distribution of reasoning tokens; it does not bound it. The
only enforced ceiling left is max_output_tokens, and hitting it mid-reasoning
returns status "incomplete" with no visible output -- while still billing every
reasoning token burned getting there.

So the cap is a real engineering decision with a real cost on both sides. Set
it low and you pay for truncated requests that produced nothing. Set it high
and you have no ceiling at all. This picks it from the distribution instead.

Run: python3 code_example.py
"""

import random

# --- The knob. Change this and watch the whole tradeoff move. ----------------
# Fraction of requests you are willing to lose to truncation. Every cap is a
# bet on the tail; this is the only honest way to state the bet.
TARGET_TRUNCATION = 0.02

SEED, REQUESTS = 3, 4000
USD_PER_OUTPUT_TOKEN = 1.20 / 1_000_000      # reasoning bills as output
ANSWER_TOKENS = 400                          # the visible answer, after thinking


# --- Liftable core: paste these three into your own repo ----------------------

def quantile(sorted_vals, q):
    """Nearest-rank quantile. No numpy, works on a list straight from a log."""
    if not sorted_vals:
        return 0
    i = min(len(sorted_vals) - 1, max(0, int(round(q * len(sorted_vals) + 0.5)) - 1))
    return sorted_vals[i]


def choose_cap(reasoning_samples, target_truncation=TARGET_TRUNCATION):
    """The cap that truncates at most `target_truncation` of observed requests.

    Read straight off your own reasoning_tokens values. A round number like
    4096 is a guess about a distribution you have already measured.
    """
    s = sorted(reasoning_samples)
    return quantile(s, 1 - target_truncation) + ANSWER_TOKENS


def waste_at_cap(reasoning_samples, cap):
    """What a cap actually costs: truncated requests, and tokens paid for nothing.

    A request truncated during reasoning produces no answer, and you are billed
    for every reasoning token it burned before the ceiling stopped it.
    """
    truncated = [r for r in reasoning_samples if r + ANSWER_TOKENS > cap]
    burned = sum(min(r, cap) for r in truncated)
    return {
        "truncated": len(truncated) / len(reasoning_samples),
        "wasted_tokens": burned,
        "wasted_usd": burned * USD_PER_OUTPUT_TOKEN,
    }


# --- The demonstration --------------------------------------------------------

# An effort level shifts the distribution; it does not bound it. These are
# lognormal-ish: a fat right tail is the whole point, because the tail is what
# a cap has to decide about.
EFFORT = {
    "minimal": (5.6, 0.45),
    "low":     (6.6, 0.60),
    "medium":  (7.5, 0.75),
    "high":    (8.3, 0.90),
}


def sample_reasoning(effort, n, rng):
    mu, sigma = EFFORT[effort]
    return [int(min(120_000, max(1, rng.lognormvariate(mu, sigma)))) for _ in range(n)]


def main():
    rng = random.Random(SEED)
    print(f"{REQUESTS} requests per effort level, seed {SEED}\n")
    print(f"{'effort':<10}{'median':>9}{'p95':>9}{'p99':>9}{'max':>9}{'spread':>9}")
    print("-" * 55)

    samples = {}
    for effort in EFFORT:
        s = sorted(sample_reasoning(effort, REQUESTS, rng))
        samples[effort] = s
        med, p95, p99 = quantile(s, 0.5), quantile(s, 0.95), quantile(s, 0.99)
        print(f"{effort:<10}{med:>9,}{p95:>9,}{p99:>9,}{s[-1]:>9,}{p99 / med:>8.1f}x")

    print("\nThe spread column is the point: one effort level is not one cost.")
    print(f"At 'high', the slowest one percent of requests think "
          f"{quantile(samples['high'], 0.99) / quantile(samples['high'], 0.5):.0f}x "
          "more than the median one.\n")

    live = samples["medium"]
    cap = choose_cap(live)
    print(f"Choosing a cap for 'medium' at a {TARGET_TRUNCATION:.0%} truncation budget")
    print(f"  max_output_tokens = {cap:,}   (p{(1 - TARGET_TRUNCATION) * 100:.0f} of "
          f"reasoning, plus {ANSWER_TOKENS} for the answer)\n")

    print(f"{'cap':>9}{'truncated':>12}{'tokens paid for nothing':>26}{'cost of that':>15}")
    print("-" * 62)
    for c in (2048, 4096, 8192, cap, 32768):
        w = waste_at_cap(live, c)
        tag = "  <- chosen" if c == cap else ""
        print(f"{c:>9,}{w['truncated']:>11.1%}{w['wasted_tokens']:>26,}"
              f"{'$' + format(w['wasted_usd'], '.2f'):>15}{tag}")

    print("\nA round number is a guess about a distribution you have already logged.")
    print("Every row above is the same model on the same work. Only the ceiling moved.")


if __name__ == "__main__":
    main()
