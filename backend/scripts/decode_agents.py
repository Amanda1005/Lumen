"""
Decode Agents - Lumen

Goal: Decode the tokenURI of each agent into structured metadata.

ERC-8004 agents can use 3 URI formats:
1. HTTPS URL (e.g. https://arcabot.ai/agent-metadata.json)
2. data: URI with base64-encoded JSON
3. data: URI with gzip + base64-encoded JSON

This script handles all three and produces a clean `agents_decoded.json`.
"""

import base64
import gzip
import json
import re
from pathlib import Path

import requests

# ============================================================
# Configuration
# ============================================================

INPUT_PATH = Path("data/agents.json")
OUTPUT_PATH = Path("data/agents_decoded.json")
HTTP_TIMEOUT = 10  # seconds


# ============================================================
# Decoders
# ============================================================

def decode_data_uri(uri: str) -> dict | None:
    """
    Decode a data: URI into a Python dict.

    Supports:
    - data:application/json;base64,XXXX
    - data:application/json;enc=gzip;level=6;base64,XXXX
    """
    # Pattern: data:application/json[;enc=gzip[;level=N]];base64,<payload>
    match = re.match(
        r"data:application/json(?:;enc=(?P<enc>gzip)[^,]*)?;base64,(?P<payload>.+)",
        uri,
        re.IGNORECASE,
    )
    if not match:
        return None

    encoding = match.group("enc")
    payload_b64 = match.group("payload")

    try:
        raw_bytes = base64.b64decode(payload_b64)

        if encoding == "gzip":
            raw_bytes = gzip.decompress(raw_bytes)

        return json.loads(raw_bytes.decode("utf-8"))

    except Exception as e:
        print(f"      decode error: {type(e).__name__}: {e}")
        return None


def fetch_http_uri(uri: str) -> dict | None:
    """Fetch and parse a JSON document from an HTTPS URL."""
    try:
        response = requests.get(uri, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"      http error: {type(e).__name__}: {e}")
        return None


def decode_agent_uri(uri: str) -> tuple[dict | None, str]:
    """
    Route to the correct decoder based on URI scheme.
    Returns (metadata_dict_or_None, uri_type_label).
    """
    if not uri or uri == "(not set)":
        return None, "empty"

    if uri.startswith("data:"):
        uri_type = "data_gzip" if "enc=gzip" in uri else "data_base64"
        return decode_data_uri(uri), uri_type

    if uri.startswith("http://") or uri.startswith("https://"):
        return fetch_http_uri(uri), "https"

    if uri.startswith("ipfs://"):
        # Convert ipfs:// to a public gateway
        gateway_url = "https://ipfs.io/ipfs/" + uri.replace("ipfs://", "")
        return fetch_http_uri(gateway_url), "ipfs"

    return None, "unknown"


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("Lumen Agent Metadata Decoder")
    print("=" * 70 + "\n")

    if not INPUT_PATH.exists():
        print(f"Input not found: {INPUT_PATH}")
        print("   Run scripts/quick_indexer.py first.")
        return

    with open(INPUT_PATH) as f:
        agents = json.load(f)

    print(f"Loaded {len(agents)} agents from {INPUT_PATH}\n")
    print("Decoding metadata...")
    print("-" * 70)

    decoded_agents = []
    stats = {
        "data_base64": 0,
        "data_gzip": 0,
        "https": 0,
        "ipfs": 0,
        "empty": 0,
        "unknown": 0,
        "decode_failed": 0,
    }

    for i, agent in enumerate(agents):
        agent_id = agent["agent_id"]
        uri = agent["token_uri"]

        metadata, uri_type = decode_agent_uri(uri)
        stats[uri_type] = stats.get(uri_type, 0) + 1

        if metadata is None and uri_type != "empty":
            stats["decode_failed"] += 1

        # Extract common fields with safe defaults
        name = (metadata or {}).get("name", "(unnamed)")
        description = (metadata or {}).get("description", "")
        skills = (metadata or {}).get("skills", [])
        endpoints = (metadata or {}).get("endpoints", [])

        decoded_agents.append({
            "agent_id": agent_id,
            "owner": agent["owner"],
            "uri_type": uri_type,
            "name": name,
            "description": description[:200],  # Truncate for sanity
            "skills_count": len(skills) if isinstance(skills, list) else 0,
            "endpoints_count": len(endpoints) if isinstance(endpoints, list) else 0,
            "raw_metadata": metadata,
        })

        if (i + 1) % 20 == 0 or i == len(agents) - 1:
            print(f"   Progress: {i + 1}/{len(agents)} agents decoded")

    print("-" * 70)
    print(f"Decoded {len(decoded_agents)} agents\n")

    # Stats
    print("URI format breakdown:")
    for uri_type, count in stats.items():
        if count > 0:
            print(f"   {uri_type:20s}: {count}")
    print()

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(decoded_agents, f, indent=2, ensure_ascii=False)
    print(f"Saved decoded data to: {OUTPUT_PATH.resolve()}\n")

    # Show insights
    show_insights(decoded_agents)


def show_insights(agents: list[dict]):
    """Print interesting findings from the decoded data."""
    print("=" * 70)
    print("Insights")
    print("=" * 70 + "\n")

    # 1. Top owners (potential teams or sybil patterns)
    owner_counts = {}
    for agent in agents:
        owner = agent["owner"]
        owner_counts[owner] = owner_counts.get(owner, 0) + 1

    multi_agent_owners = sorted(
        [(owner, count) for owner, count in owner_counts.items() if count > 1],
        key=lambda x: -x[1],
    )

    print(f"Owners with multiple agents ({len(multi_agent_owners)} total):")
    for owner, count in multi_agent_owners[:10]:
        print(f"   {owner}  ->  {count} agents")
    if not multi_agent_owners:
        print("   (none)")
    print()

    # 2. Named vs unnamed
    named = [a for a in agents if a["name"] != "(unnamed)"]
    print(f"Named agents: {len(named)}/{len(agents)}")
    print()

    # 3. Sample of decoded names
    print("Sample of agent names (first 10 named):")
    for agent in named[:10]:
        name = agent["name"]
        desc = agent["description"][:60]
        suffix = "..." if len(agent["description"]) > 60 else ""
        print(f"   #{agent['agent_id']:>3}  {name}")
        if desc:
            print(f"         {desc}{suffix}")
    print()

    print("=" * 70)
    print(f"Day 1.5 Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()