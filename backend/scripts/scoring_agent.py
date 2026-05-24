"""
Lumen Scoring Agent - 0-100 credit score per agent.
"""

import json
from pathlib import Path

INPUT = Path("data/agents_enriched.json")
OUTPUT = Path("data/agents_scored.json")


def score_completeness(agent: dict) -> int:
    """25% - based on metadata fields present."""
    meta = agent.get("raw_metadata") or {}
    fields = [meta.get("name"), meta.get("description"), meta.get("image"),
              meta.get("homepage") or meta.get("url") or meta.get("external_url"),
              meta.get("skills") or meta.get("services")]
    return round(sum(1 for f in fields if f) / 5 * 100)


def score_capability(agent: dict) -> int:
    """25% - skills + endpoints + tools."""
    meta = agent.get("raw_metadata") or {}
    skills = len(meta.get("skills") or [])
    endpoints = len(meta.get("endpoints") or [])
    tools = len(meta.get("tools") or [])
    total = skills + endpoints + tools
    return min(100, total * 20)


def score_owner_reputation(agent: dict) -> int:
    """20% - sybil penalty."""
    risk = agent.get("risk_level", "SAFE")
    return {"SAFE": 100, "SUSPICIOUS": 50, "SYBIL": 5}.get(risk, 50)


def score_verifiability(agent: dict) -> int:
    """15% - has external proofs."""
    meta = agent.get("raw_metadata") or {}
    score = 0
    if meta.get("homepage") or meta.get("url") or meta.get("external_url"):
        score += 40
    if meta.get("endpoints"):
        score += 30
    if meta.get("schema"):
        score += 30
    return min(100, score)


def score_activity(agent: dict) -> int:
    """15% - feedback signals, penalized for self-feedback."""
    rep = agent.get("reputation") or {}
    count = rep.get("feedback_count", 0)
    clients = rep.get("unique_client_count", 0)

    if count == 0:
        return 0
    # Penalize feedback-stuffing (1 client = self-feedback)
    if clients <= 1:
        return min(20, count // 5)  # cap at 20
    return min(100, count * 2 + clients * 5)


def compute_lumen_score(agent: dict) -> dict:
    scores = {
        "completeness":      score_completeness(agent),
        "capability":        score_capability(agent),
        "owner_reputation":  score_owner_reputation(agent),
        "verifiability":     score_verifiability(agent),
        "activity":          score_activity(agent),
    }
    weights = {"completeness": 0.25, "capability": 0.25,
               "owner_reputation": 0.20, "verifiability": 0.15,
               "activity": 0.15}
    total = sum(scores[k] * weights[k] for k in scores)

    return {
        "lumen_score": round(total),
        "breakdown": scores,
        "grade": grade(total),
    }


def grade(score: float) -> str:
    if score >= 80: return "A"
    if score >= 60: return "B"
    if score >= 40: return "C"
    if score >= 20: return "D"
    return "F"


def main():
    print("=" * 70)
    print("Lumen Scoring Agent")
    print("=" * 70 + "\n")

    with open(INPUT) as f:
        agents = json.load(f)

    print(f"Scoring {len(agents)} agents...\n")

    scored = []
    for agent in agents:
        result = compute_lumen_score(agent)
        merged = dict(agent)
        merged.update(result)
        scored.append(merged)

    scored.sort(key=lambda a: -a["lumen_score"])

    with open(OUTPUT, "w") as f:
        json.dump(scored, f, indent=2, ensure_ascii=False, default=str)

    print(f"{'Rank':<5} {'ID':<5} {'Score':<7} {'Grade':<6} {'Risk':<10} {'Name'}")
    print("-" * 70)
    for i, a in enumerate(scored[:20], 1):
        name = (a.get("name") or "(unnamed)")[:30]
        print(f"{i:<5} {a['agent_id']:<5} {a['lumen_score']:<7} "
              f"{a['grade']:<6} {a.get('risk_level','?'):<10} {name}")

    print(f"\nSaved to: {OUTPUT}")


if __name__ == "__main__":
    main()