import json
import os
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

INPUT = Path("data/agents_scored.json")
OUTPUT = Path("data/agents_with_comments.json")

SYSTEM_PROMPT = """You are a senior research analyst at Lumen, an institutional-grade rating agency for on-chain AI agents (like Bloomberg for AI agents).

Write a short analyst note (60-90 words) for the agent given below. Follow these rules strictly:

TONE:
- Institutional research, not casual AI text
- Evidence-backed, not vague
- Short sentences, no fluff
- Open with "Lumen analysts observed..." or similar institutional opener

STRUCTURE:
1. Lead with the key finding (1 sentence)
2. Support with 1-2 specific evidence points from the data
3. End with a clear stance (e.g. "Recommend monitoring", "Avoid", "Notable build quality")

DO NOT:
- Use marketing language
- Repeat the raw score
- Use words like "amazing", "great", "exciting"
- Start with "This agent is..."

OUTPUT: Plain text only, no markdown, no headers."""


def build_agent_prompt(agent: dict) -> str:
    """Compact data summary for Claude."""
    breakdown = agent.get("breakdown", {})
    rep = agent.get("reputation", {})
    evidence = agent.get("cluster_evidence", [])

    lines = [
        f"Agent ID: {agent['agent_id']}",
        f"Name: {agent.get('name', '(unnamed)')}",
        f"Description: {agent.get('description', '')[:200]}",
        f"Lumen Score: {agent['lumen_score']}/100 (Grade {agent['grade']})",
        f"Risk Level: {agent.get('risk_level', 'UNKNOWN')}",
        f"Cluster size: {agent.get('cluster_size', 1)} agents from same owner",
        "",
        "Score breakdown:",
        f"  - Completeness: {breakdown.get('completeness', 0)}/100",
        f"  - Capability: {breakdown.get('capability', 0)}/100",
        f"  - Owner Reputation: {breakdown.get('owner_reputation', 0)}/100",
        f"  - Verifiability: {breakdown.get('verifiability', 0)}/100",
        f"  - Activity: {breakdown.get('activity', 0)}/100",
        "",
        f"On-chain feedback: {rep.get('feedback_count', 0)} signals from "
        f"{rep.get('unique_client_count', 0)} unique clients",
    ]

    if evidence:
        lines.append("")
        lines.append("Risk evidence:")
        for e in evidence:
            lines.append(f"  - {e}")

    return "\n".join(lines)


def generate_comment(agent: dict) -> str:
    """Call Claude to generate an analyst note."""
    user_prompt = build_agent_prompt(agent)

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text.strip()


def main():
    print("=" * 70)
    print("Lumen Comment Agent")
    print("=" * 70 + "\n")

    with open(INPUT) as f:
        agents = json.load(f)

    print(f"Generating analyst notes for {len(agents)} agents...")
    print("(This will take ~2-5 minutes and cost ~$0.30)\n")

    # Strategy: full notes for top 8 SAFE + 1 representative SYBIL
    # The other 88 sybils share the same note (since they're identical clones)
    safe_agents = [a for a in agents if a.get("risk_level") == "SAFE"]
    sybil_agents = [a for a in agents if a.get("risk_level") == "SYBIL"]

    print(f"Strategy: {len(safe_agents)} unique SAFE notes + 1 shared SYBIL note")
    print(f"(saves ~{len(sybil_agents) - 1} API calls)\n")

    # Generate SAFE notes individually
    comments = {}
    for i, agent in enumerate(safe_agents, 1):
        print(f"[{i}/{len(safe_agents)}] Agent #{agent['agent_id']} ({agent.get('name', '?')[:30]})...")
        try:
            comment = generate_comment(agent)
            comments[agent["agent_id"]] = comment
            print(f"   → {comment[:80]}...")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            comments[agent["agent_id"]] = None

    # Generate ONE shared note for the sybil cluster
    if sybil_agents:
        print(f"\n[Sybil cluster] Generating shared note for {len(sybil_agents)} clones...")
        try:
            sybil_note = generate_comment(sybil_agents[0])
            print(f"   → {sybil_note[:80]}...")
            for agent in sybil_agents:
                comments[agent["agent_id"]] = sybil_note
        except Exception as e:
            print(f"   ✗ Failed: {e}")

    # Merge back
    for agent in agents:
        agent["analyst_note"] = comments.get(agent["agent_id"])

    with open(OUTPUT, "w") as f:
        json.dump(agents, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n Saved to {OUTPUT}")
    print(f"   {sum(1 for c in comments.values() if c)} notes generated")


if __name__ == "__main__":
    main()