"""
Inspect Safe Agents

Goal: Take a deep look at the 8 SAFE agents (non-sybil) on Mantle.

These are the legitimate agents that Lumen wants to highlight in the
ranking. Understanding them tells us:
1. What "good agent metadata" looks like
2. Which agents deserve top-tier scores
3. What dimensions actually differentiate quality agents

Output: A demo-ready inspection report.
"""

import json
from pathlib import Path

INPUT_PATH = Path("data/agents_clustered.json")
OUTPUT_PATH = Path("data/safe_agents_report.json")


def format_field(value, max_len: int = 100) -> str:
    """Pretty-print a field, truncating long values."""
    if value is None or value == "":
        return "(empty)"
    text = str(value)
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def extract_metadata_dimensions(metadata: dict | None) -> dict:
    """
    Extract Lumen's 5 scoring dimensions from raw metadata.
    Returns a dict with raw signals for each dimension.
    """
    if not metadata:
        return {
            "completeness": 0,
            "has_description": False,
            "has_skills": False,
            "has_endpoints": False,
            "has_homepage": False,
            "skills_count": 0,
            "endpoints_count": 0,
            "description_length": 0,
        }

    description = metadata.get("description", "") or ""
    skills = metadata.get("skills", []) or []
    endpoints = metadata.get("endpoints", []) or []
    homepage = metadata.get("homepage") or metadata.get("url") or metadata.get("website")

    # Completeness score: how many key fields are filled?
    fields_present = sum([
        bool(metadata.get("name")),
        bool(description),
        bool(skills),
        bool(endpoints),
        bool(homepage),
    ])
    completeness = round((fields_present / 5) * 100)

    return {
        "completeness": completeness,
        "has_description": bool(description),
        "has_skills": bool(skills),
        "has_endpoints": bool(endpoints),
        "has_homepage": bool(homepage),
        "skills_count": len(skills) if isinstance(skills, list) else 0,
        "endpoints_count": len(endpoints) if isinstance(endpoints, list) else 0,
        "description_length": len(description),
    }


def inspect_agent(agent: dict) -> dict:
    """Build a detailed inspection record for one agent."""
    metadata = agent.get("raw_metadata") or {}
    dimensions = extract_metadata_dimensions(metadata)

    return {
        "agent_id": agent["agent_id"],
        "name": agent.get("name", "(unnamed)"),
        "owner": agent["owner"],
        "owner_short": agent["owner"][:6] + "..." + agent["owner"][-4:],
        "uri_type": agent["uri_type"],
        "description": agent.get("description", ""),
        "risk_level": agent.get("risk_level", "UNKNOWN"),
        "dimensions": dimensions,
        "raw_metadata_keys": list(metadata.keys()) if metadata else [],
        "skills": metadata.get("skills", []) if metadata else [],
        "endpoints": metadata.get("endpoints", []) if metadata else [],
        "homepage": (
            metadata.get("homepage")
            or metadata.get("url")
            or metadata.get("website")
        ) if metadata else None,
    }


def print_agent_card(agent: dict, index: int):
    """Print one agent as a card for visual inspection."""
    print("=" * 70)
    print(f"#{index}  Agent ID: {agent['agent_id']}  |  {agent['name']}")
    print("=" * 70)
    print(f"  Owner:        {agent['owner']}")
    print(f"  URI type:     {agent['uri_type']}")
    print(f"  Risk:         {agent['risk_level']}")
    print(f"  Completeness: {agent['dimensions']['completeness']}/100")
    print()
    print(f"  Description:")
    desc = agent["description"] or "(empty)"
    # Print description with indent
    for line in desc.split("\n")[:5]:  # max 5 lines
        print(f"    {line[:80]}")
    print()

    if agent["raw_metadata_keys"]:
        print(f"  Metadata fields: {', '.join(agent['raw_metadata_keys'])}")

    if agent["skills"]:
        print(f"  Skills ({len(agent['skills'])}):")
        for skill in agent["skills"][:3]:
            if isinstance(skill, dict):
                name = skill.get("name") or skill.get("id") or "(unnamed skill)"
                print(f"    - {name}")
            else:
                print(f"    - {str(skill)[:60]}")

    if agent["endpoints"]:
        print(f"  Endpoints ({len(agent['endpoints'])}):")
        for endpoint in agent["endpoints"][:3]:
            if isinstance(endpoint, dict):
                url = endpoint.get("url") or endpoint.get("uri") or "(no url)"
                print(f"    - {format_field(url, 60)}")
            else:
                print(f"    - {format_field(endpoint, 60)}")

    if agent["homepage"]:
        print(f"  Homepage: {agent['homepage']}")

    print()


def rank_safe_agents(safe_agents: list[dict]) -> list[dict]:
    """
    Pre-rank safe agents by completeness for demo purposes.
    This is a placeholder for the real scoring algorithm (coming tomorrow).
    """
    return sorted(
        safe_agents,
        key=lambda a: (
            -a["dimensions"]["completeness"],
            -a["dimensions"]["skills_count"],
            -a["dimensions"]["endpoints_count"],
            -a["dimensions"]["description_length"],
        ),
    )


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("Lumen Safe-Agent Inspector")
    print("=" * 70 + "\n")

    if not INPUT_PATH.exists():
        print(f"Input not found: {INPUT_PATH}")
        print("   Run scripts/cluster_detector.py first.")
        return

    with open(INPUT_PATH) as f:
        agents = json.load(f)

    print(f"Loaded {len(agents)} agents\n")

    # Filter to SAFE only
    safe_agents = [a for a in agents if a.get("risk_level") == "SAFE"]
    print(f"Found {len(safe_agents)} SAFE agents (Lumen's demo headliners)\n")

    # Inspect each one
    inspected = [inspect_agent(a) for a in safe_agents]

    # Rank by quality signals
    ranked = rank_safe_agents(inspected)

    # Print each as a card
    print("\n" + "=" * 70)
    print("Detailed Inspection (ranked by completeness)")
    print("=" * 70 + "\n")

    for i, agent in enumerate(ranked, 1):
        print_agent_card(agent, i)

    # Summary
    print_summary(ranked)

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(ranked, f, indent=2, ensure_ascii=False)
    print(f"Saved inspection report to: {OUTPUT_PATH.resolve()}")


def print_summary(ranked: list[dict]):
    """Print a tabular summary of all safe agents."""
    print("=" * 70)
    print("Summary Table (demo cheat sheet)")
    print("=" * 70 + "\n")

    print(f"  {'Rank':<5} {'ID':<5} {'Name':<25} {'Compl.':<7} {'Skills':<7} "
          f"{'Endpts':<7} {'URI':<10}")
    print("  " + "-" * 68)

    for i, agent in enumerate(ranked, 1):
        name = agent["name"][:24]
        compl = agent["dimensions"]["completeness"]
        skills = agent["dimensions"]["skills_count"]
        endpts = agent["dimensions"]["endpoints_count"]
        uri_type = agent["uri_type"][:9]

        print(f"  {i:<5} {agent['agent_id']:<5} {name:<25} {compl:<7} "
              f"{skills:<7} {endpts:<7} {uri_type:<10}")

    print()


if __name__ == "__main__":
    main()