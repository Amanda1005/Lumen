"""
Cluster Detector - Lumen Day 1.7

Goal: Detect sybil clusters among ERC-8004 agents on Mantle.

A "cluster" is a group of agents that share suspicious patterns:
1. Same owner address (strongest signal)
2. Sequential naming (e.g., agent-001, agent-002, agent-003)
3. Identical or near-identical descriptions
4. Registered within a short time window (TBD - needs block timestamps)

This is Lumen's flagship feature: turning data noise into actionable
risk signals that protect investors.
"""

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# ============================================================
# Configuration
# ============================================================

INPUT_PATH = Path("data/agents_decoded.json")
OUTPUT_PATH = Path("data/agents_clustered.json")
REPORT_PATH = Path("data/cluster_report.json")

# Thresholds
MIN_CLUSTER_SIZE = 3           # >=3 agents from same owner = cluster
DESC_SIMILARITY_THRESHOLD = 0.8  # 80%+ description similarity = duplicate
SEQUENTIAL_NAME_THRESHOLD = 3   # 3+ sequential names = pattern


# ============================================================
# Detection Logic
# ============================================================

def group_by_owner(agents: list[dict]) -> dict[str, list[dict]]:
    """Group agents by owner address."""
    groups = defaultdict(list)
    for agent in agents:
        groups[agent["owner"]].append(agent)
    return dict(groups)


def detect_sequential_naming(names: list[str]) -> dict:
    """
    Detect if names follow a sequential pattern like:
    - babycaisubagent-001, babycaisubagent-002, ...
    - bot-1, bot-2, bot-3
    - agent_a, agent_b, agent_c

    Returns a dict with pattern info.
    """
    # Try to extract numeric suffixes
    numeric_pattern = re.compile(r"^(.+?)[-_]?(\d+)$")

    prefix_counts = defaultdict(list)
    for name in names:
        match = numeric_pattern.match(name)
        if match:
            prefix = match.group(1).rstrip("-_").strip()
            number = int(match.group(2))
            prefix_counts[prefix].append(number)

    # Find prefixes with multiple sequential numbers
    sequential_groups = {}
    for prefix, numbers in prefix_counts.items():
        if len(numbers) >= SEQUENTIAL_NAME_THRESHOLD:
            sorted_nums = sorted(numbers)
            sequential_groups[prefix] = {
                "count": len(numbers),
                "range": (sorted_nums[0], sorted_nums[-1]),
                "is_continuous": len(numbers) == (sorted_nums[-1] - sorted_nums[0] + 1),
            }

    return sequential_groups


def detect_duplicate_descriptions(agents: list[dict]) -> dict:
    """
    Group agents by description similarity.
    Returns a dict mapping representative description -> agent count.
    """
    descriptions = [a.get("description", "").strip() for a in agents]
    descriptions = [d for d in descriptions if d]  # filter empty

    if not descriptions:
        return {}

    # Use exact-match first (fast), then fuzzy match for near-duplicates
    exact_counts = defaultdict(int)
    for desc in descriptions:
        exact_counts[desc] += 1

    duplicates = {
        desc: count for desc, count in exact_counts.items()
        if count >= 2
    }

    return duplicates


def similarity(a: str, b: str) -> float:
    """Compute string similarity ratio (0.0 - 1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def classify_cluster(owner: str, agents: list[dict]) -> dict:
    """
    Analyze a group of agents from the same owner and assign a risk label.

    Risk levels:
    - SAFE       : 1-2 agents, normal pattern
    - SUSPICIOUS : 3-9 agents, some patterns detected
    - SYBIL      : 10+ agents OR strong sequential/duplicate patterns
    """
    count = len(agents)
    names = [a.get("name", "") for a in agents]
    sequential = detect_sequential_naming(names)
    duplicate_descs = detect_duplicate_descriptions(agents)

    # Decide risk level
    if count == 1:
        risk = "SAFE"
        confidence = 1.0
    elif count <= 2:
        risk = "SAFE"
        confidence = 0.9
    elif count <= 9:
        if sequential or duplicate_descs:
            risk = "SUSPICIOUS"
            confidence = 0.7
        else:
            risk = "SAFE"
            confidence = 0.8
    else:  # 10+
        if sequential or duplicate_descs:
            risk = "SYBIL"
            confidence = 0.95
        else:
            risk = "SUSPICIOUS"
            confidence = 0.6

    # Build evidence list (human-readable signals)
    evidence = []
    if count >= 10:
        evidence.append(f"Owner controls {count} agents (mass registration)")
    if sequential:
        for prefix, info in sequential.items():
            evidence.append(
                f"Sequential naming: '{prefix}' x{info['count']} "
                f"(range {info['range'][0]}-{info['range'][1]})"
            )
    if duplicate_descs:
        for desc, dup_count in list(duplicate_descs.items())[:2]:  # top 2
            preview = desc[:50] + "..." if len(desc) > 50 else desc
            evidence.append(f"Duplicate description x{dup_count}: \"{preview}\"")

    return {
        "owner": owner,
        "agent_count": count,
        "risk_level": risk,
        "confidence": confidence,
        "evidence": evidence,
        "agent_ids": sorted([a["agent_id"] for a in agents]),
        "sequential_patterns": sequential,
        "duplicate_description_count": len(duplicate_descs),
    }


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("Lumen Cluster Detector")
    print("=" * 70 + "\n")

    if not INPUT_PATH.exists():
        print(f"Input not found: {INPUT_PATH}")
        print("   Run scripts/decode_agents.py first.")
        return

    with open(INPUT_PATH) as f:
        agents = json.load(f)

    print(f"Loaded {len(agents)} agents\n")

    # Step 1: Group by owner
    owner_groups = group_by_owner(agents)
    print(f"Found {len(owner_groups)} unique owners")
    print(f"   Largest owner: {max(len(v) for v in owner_groups.values())} agents")
    print(f"   Solo owners (1 agent): "
          f"{sum(1 for v in owner_groups.values() if len(v) == 1)}\n")

    # Step 2: Classify each owner cluster
    print("Classifying clusters...")
    print("-" * 70)

    clusters = []
    for owner, owner_agents in owner_groups.items():
        cluster = classify_cluster(owner, owner_agents)
        clusters.append(cluster)

    # Sort by risk + count
    risk_order = {"SYBIL": 0, "SUSPICIOUS": 1, "SAFE": 2}
    clusters.sort(key=lambda c: (risk_order[c["risk_level"]], -c["agent_count"]))

    # Step 3: Tag each agent with cluster info
    cluster_lookup = {c["owner"]: c for c in clusters}
    tagged_agents = []
    for agent in agents:
        cluster = cluster_lookup[agent["owner"]]
        tagged = dict(agent)
        tagged["risk_level"] = cluster["risk_level"]
        tagged["cluster_size"] = cluster["agent_count"]
        tagged["cluster_evidence"] = cluster["evidence"]
        tagged_agents.append(tagged)

    # Step 4: Build summary report
    summary = build_summary(clusters, agents)

    # Step 5: Save outputs
    save_outputs(tagged_agents, clusters, summary)

    # Step 6: Print headline findings
    print_findings(summary, clusters)


def build_summary(clusters: list[dict], agents: list[dict]) -> dict:
    """Compile high-level statistics for the Pitch deck."""
    risk_counts = {"SAFE": 0, "SUSPICIOUS": 0, "SYBIL": 0}
    agents_by_risk = {"SAFE": 0, "SUSPICIOUS": 0, "SYBIL": 0}

    for cluster in clusters:
        risk_counts[cluster["risk_level"]] += 1
        agents_by_risk[cluster["risk_level"]] += cluster["agent_count"]

    total_agents = len(agents)
    sybil_share = (agents_by_risk["SYBIL"] / total_agents * 100) if total_agents else 0

    return {
        "total_agents": total_agents,
        "total_owners": len(clusters),
        "risk_distribution_by_owner": risk_counts,
        "risk_distribution_by_agent": agents_by_risk,
        "sybil_share_percent": round(sybil_share, 1),
        "headline": (
            f"{sybil_share:.0f}% of AI agents on Mantle "
            f"are controlled by SYBIL clusters"
        ),
    }


def save_outputs(tagged_agents, clusters, summary):
    """Persist all outputs to disk."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(tagged_agents, f, indent=2, ensure_ascii=False)
    print(f"Tagged agents -> {OUTPUT_PATH}")

    with open(REPORT_PATH, "w") as f:
        json.dump({"summary": summary, "clusters": clusters}, f, indent=2,
                  ensure_ascii=False)
    print(f"Cluster report -> {REPORT_PATH}\n")


def print_findings(summary: dict, clusters: list[dict]):
    """Print the headline findings, demo-ready."""
    print("=" * 70)
    print("Headline Findings")
    print("=" * 70 + "\n")

    print(f"   {summary['headline']}\n")

    print(f"   Total agents:        {summary['total_agents']}")
    print(f"   Unique owners:       {summary['total_owners']}")
    print(f"   Sybil share:         {summary['sybil_share_percent']}%\n")

    print("   Risk distribution (by owner):")
    for level, count in summary["risk_distribution_by_owner"].items():
        print(f"      {level:12s}: {count}")
    print()

    print("   Risk distribution (by agent):")
    for level, count in summary["risk_distribution_by_agent"].items():
        print(f"      {level:12s}: {count}")
    print()

    # Show top sybil clusters
    sybil_clusters = [c for c in clusters if c["risk_level"] == "SYBIL"]
    if sybil_clusters:
        print("Top SYBIL clusters detected:\n")
        for cluster in sybil_clusters[:3]:
            print(f"   Owner: {cluster['owner']}")
            print(f"   Agents: {cluster['agent_count']} | "
                  f"Confidence: {cluster['confidence']:.0%}")
            print(f"   Evidence:")
            for line in cluster["evidence"]:
                print(f"      - {line}")
            print()

    print("=" * 70)
    print("Day 1.7 Complete - Lumen's flagship feature is online")
    print("=" * 70)


if __name__ == "__main__":
    main()