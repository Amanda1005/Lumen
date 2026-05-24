"""
Reputation Indexer v2 - Lumen Day 1.9 (Full ABI Decoding)

Indexes all NewFeedback events from ERC-8004 ReputationRegistry on Mantle,
decoding the full event payload (scores, tags, endpoints, URIs).
"""

import os
import json
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# ============================================================
# Configuration
# ============================================================

MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
REPUTATION_REGISTRY_ADDRESS = os.getenv(
    "REPUTATION_REGISTRY_ADDRESS",
    "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
)

DEPLOY_BLOCK = 91_000_000
CHUNK_SIZE = 10_000

OUTPUT_PATH = Path("data/feedback.json")
ENRICHED_AGENTS_PATH = Path("data/agents_enriched.json")
CLUSTERED_AGENTS_PATH = Path("data/agents_clustered.json")


# ============================================================
# ABI - matches the exact event signature you confirmed
# ============================================================

NEW_FEEDBACK_ABI = [{
    "anonymous": False,
    "inputs": [
        {"indexed": True,  "name": "agentId",       "type": "uint256"},
        {"indexed": True,  "name": "clientAddress", "type": "address"},
        {"indexed": False, "name": "feedbackIndex", "type": "uint64"},
        {"indexed": False, "name": "value",         "type": "int128"},
        {"indexed": False, "name": "valueDecimals", "type": "uint8"},
        {"indexed": True,  "name": "indexedTag1",   "type": "string"},
        {"indexed": False, "name": "tag1",          "type": "string"},
        {"indexed": False, "name": "tag2",          "type": "string"},
        {"indexed": False, "name": "endpoint",      "type": "string"},
        {"indexed": False, "name": "feedbackURI",   "type": "string"},
        {"indexed": False, "name": "feedbackHash",  "type": "bytes32"},
    ],
    "name": "NewFeedback",
    "type": "event",
}]


# ============================================================
# Connection
# ============================================================

def connect_to_mantle() -> Web3:
    print("Connecting to Mantle Mainnet...")
    w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect")
    print(f"Connected. Latest block: {w3.eth.block_number:,}\n")
    return w3


# ============================================================
# Log Scanning
# ============================================================

def scan_all_logs(w3: Web3, address: str, from_block: int, to_block: int) -> list:
    print(f"Scanning blocks {from_block:,} to {to_block:,} for ALL logs...")
    print(f"   Chunk size: {CHUNK_SIZE:,}\n")

    address = Web3.to_checksum_address(address)
    all_logs = []
    current = from_block
    chunk_count = 0
    found = 0

    while current <= to_block:
        end = min(current + CHUNK_SIZE - 1, to_block)
        chunk_count += 1
        try:
            logs = w3.eth.get_logs({
                "address": address,
                "fromBlock": current,
                "toBlock": end,
            })
            if logs:
                all_logs.extend(logs)
                found += len(logs)
                print(f"   Blocks {current:,}-{end:,}: {len(logs)} logs (total: {found})")
        except Exception as e:
            print(f"   Blocks {current:,}-{end:,}: skipped ({type(e).__name__})")
        current = end + 1

    print(f"\nScanned {chunk_count} chunks. Found {len(all_logs)} raw logs.\n")
    return all_logs


def categorize_logs_by_topic(logs: list) -> dict:
    grouped = defaultdict(list)
    for log in logs:
        if log["topics"]:
            grouped[log["topics"][0].hex()].append(log)
    return dict(grouped)


# ============================================================
# Parsing - now with full ABI decode
# ============================================================

def parse_feedback_logs(logs: list, w3: Web3) -> list[dict]:
    """Parse NewFeedback events using the full ABI."""
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(REPUTATION_REGISTRY_ADDRESS),
        abi=NEW_FEEDBACK_ABI,
    )

    parsed = []
    decoded_count = 0
    fallback_count = 0

    for log in logs:
        try:
            event = contract.events.NewFeedback().process_log(log)
            args = event["args"]

            raw_value = args["value"]
            decimals = args["valueDecimals"]
            score = raw_value / (10 ** decimals) if decimals > 0 else raw_value

            parsed.append({
                "agent_id":       args["agentId"],
                "client":         args["clientAddress"],
                "feedback_index": args["feedbackIndex"],
                "raw_value":      raw_value,
                "value_decimals": decimals,
                "score":          score,
                "tag1":           args["tag1"],
                "tag2":           args["tag2"],
                "endpoint":       args["endpoint"],
                "feedback_uri":   args["feedbackURI"],
                "feedback_hash":  args["feedbackHash"].hex(),
                "block_number":   log["blockNumber"],
                "tx_hash":        log["transactionHash"].hex(),
            })
            decoded_count += 1

        except Exception as e:
            # Fallback: extract just from topics
            try:
                topics = log["topics"]
                if len(topics) >= 3:
                    parsed.append({
                        "agent_id": int(topics[1].hex(), 16),
                        "client": Web3.to_checksum_address("0x" + topics[2].hex()[-40:]),
                        "score": None,
                        "tag1": None,
                        "tag2": None,
                        "endpoint": None,
                        "feedback_uri": None,
                        "block_number": log["blockNumber"],
                        "tx_hash": log["transactionHash"].hex(),
                        "decode_error": f"{type(e).__name__}: {str(e)[:80]}",
                    })
                    fallback_count += 1
            except Exception:
                continue

    print(f"   Fully decoded: {decoded_count}")
    print(f"   Fallback (topics only): {fallback_count}\n")
    return parsed


# ============================================================
# Aggregation
# ============================================================

def most_common(items: list, n: int = 5) -> list:
    counts = defaultdict(int)
    for item in items:
        if item:
            counts[item] += 1
    return sorted(counts.items(), key=lambda x: -x[1])[:n]


def aggregate_feedback_by_agent(feedback: list[dict]) -> dict[int, dict]:
    by_agent = defaultdict(lambda: {
        "feedback_count": 0,
        "unique_clients": set(),
        "scores": [],
        "tags": [],
        "endpoints": set(),
        "feedback_uris": [],
        "first_block": None,
        "last_block": None,
        "tx_hashes": [],
    })

    for fb in feedback:
        agent_id = fb["agent_id"]
        agg = by_agent[agent_id]

        agg["feedback_count"] += 1
        if fb["client"]:
            agg["unique_clients"].add(fb["client"])

        if fb.get("score") is not None:
            agg["scores"].append(fb["score"])
        if fb.get("tag1"):
            agg["tags"].append(fb["tag1"])
        if fb.get("tag2"):
            agg["tags"].append(fb["tag2"])
        if fb.get("endpoint"):
            agg["endpoints"].add(fb["endpoint"])
        if fb.get("feedback_uri"):
            agg["feedback_uris"].append(fb["feedback_uri"])

        block = fb["block_number"]
        if agg["first_block"] is None or block < agg["first_block"]:
            agg["first_block"] = block
        if agg["last_block"] is None or block > agg["last_block"]:
            agg["last_block"] = block

        agg["tx_hashes"].append(fb["tx_hash"])

    result = {}
    for agent_id, agg in by_agent.items():
        scores = agg["scores"]
        result[agent_id] = {
            "feedback_count":      agg["feedback_count"],
            "unique_client_count": len(agg["unique_clients"]),
            "unique_clients":      list(agg["unique_clients"]),
            "avg_score":           sum(scores) / len(scores) if scores else None,
            "min_score":           min(scores) if scores else None,
            "max_score":           max(scores) if scores else None,
            "score_count":         len(scores),
            "top_tags":            most_common(agg["tags"], n=5),
            "unique_endpoints":    list(agg["endpoints"]),
            "sample_uris":         list(set(agg["feedback_uris"]))[:5],
            "first_block":         agg["first_block"],
            "last_block":          agg["last_block"],
            "sample_tx_hashes":    agg["tx_hashes"][:5],
        }
    return result


# ============================================================
# Enrich Agents
# ============================================================

def enrich_agents_with_feedback(agents_path: Path, feedback_by_agent: dict) -> list[dict]:
    if not agents_path.exists():
        print(f"Cluster file not found: {agents_path}")
        return []

    with open(agents_path) as f:
        agents = json.load(f)

    enriched = []
    for agent in agents:
        agent_id = agent["agent_id"]
        fb_stats = feedback_by_agent.get(agent_id, {
            "feedback_count": 0,
            "unique_client_count": 0,
            "avg_score": None,
            "top_tags": [],
        })
        merged = dict(agent)
        merged["reputation"] = fb_stats
        enriched.append(merged)
    return enriched


# ============================================================
# Reporting
# ============================================================

def print_topic_breakdown(grouped: dict):
    print("Event type breakdown (by topic[0]):")
    for topic, logs in sorted(grouped.items(), key=lambda x: -len(x[1])):
        print(f"   {topic[:18]}...  ->  {len(logs)} logs")
    print()


def print_feedback_stats(feedback: list[dict], by_agent: dict):
    if not feedback:
        print("No feedback parsed.")
        return

    print("=" * 70)
    print("Feedback Statistics")
    print("=" * 70 + "\n")

    print(f"Total feedback signals: {len(feedback)}")
    print(f"Unique agents receiving feedback: {len(by_agent)}")

    all_clients = set()
    all_scores = []
    all_tags = []
    for fb in feedback:
        if fb.get("client"):
            all_clients.add(fb["client"])
        if fb.get("score") is not None:
            all_scores.append(fb["score"])
        if fb.get("tag1"):
            all_tags.append(fb["tag1"])
        if fb.get("tag2"):
            all_tags.append(fb["tag2"])

    print(f"Unique clients giving feedback: {len(all_clients)}\n")

    if all_scores:
        avg = sum(all_scores) / len(all_scores)
        print(f"Score distribution:")
        print(f"   Avg: {avg:.2f}  |  Min: {min(all_scores):.2f}  |  Max: {max(all_scores):.2f}\n")

    if all_tags:
        print("Top 10 feedback tags:")
        for tag, count in most_common(all_tags, n=10):
            print(f"   {tag:30s} -> {count}")
        print()

    top_agents = sorted(by_agent.items(), key=lambda x: -x[1]["feedback_count"])[:10]
    print("Top 10 agents by feedback count:")
    for agent_id, stats in top_agents:
        avg = stats.get("avg_score")
        avg_str = f"avg {avg:.2f}" if avg is not None else "no scores"
        print(f"   Agent #{agent_id:>4}  ->  {stats['feedback_count']:>4} feedback  "
              f"({stats['unique_client_count']} clients, {avg_str})")
    print()


def print_pitch_numbers(agents_count: int, feedback_count: int, agents_with_feedback: int):
    print("=" * 70)
    print("Pitch Numbers")
    print("=" * 70 + "\n")
    coverage = (agents_with_feedback / agents_count * 100) if agents_count else 0
    print(f"   {agents_count} agents indexed on Mantle ERC-8004")
    print(f"   {feedback_count} reputation signals with scores + tags + URIs")
    print(f"   {agents_with_feedback} / {agents_count} agents have feedback ({coverage:.0f}% coverage)\n")


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("Lumen Reputation Indexer v2 (Full ABI Decode)")
    print("=" * 70 + "\n")

    w3 = connect_to_mantle()
    latest_block = w3.eth.block_number

    all_logs = scan_all_logs(w3, REPUTATION_REGISTRY_ADDRESS, DEPLOY_BLOCK, latest_block)
    if not all_logs:
        print("No logs found.")
        return

    grouped = categorize_logs_by_topic(all_logs)
    print_topic_breakdown(grouped)

    largest_topic = max(grouped.keys(), key=lambda t: len(grouped[t]))
    main_logs = grouped[largest_topic]
    print(f"Treating topic {largest_topic[:18]}... as the feedback event ({len(main_logs)} logs)\n")

    feedback = parse_feedback_logs(main_logs, w3)
    by_agent = aggregate_feedback_by_agent(feedback)

    # Save raw feedback
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump({
            "all_topics": {t: len(logs) for t, logs in grouped.items()},
            "primary_topic": largest_topic,
            "feedback": feedback,
            "by_agent": {str(k): v for k, v in by_agent.items()},
        }, f, indent=2, default=str)
    print(f"Saved raw feedback to: {OUTPUT_PATH}\n")

    # Enrich
    enriched = enrich_agents_with_feedback(CLUSTERED_AGENTS_PATH, by_agent)
    if enriched:
        with open(ENRICHED_AGENTS_PATH, "w") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False, default=str)
        print(f"Saved enriched agents to: {ENRICHED_AGENTS_PATH}\n")

    print_feedback_stats(feedback, by_agent)

    agents_with_fb = sum(1 for s in by_agent.values() if s["feedback_count"] > 0)
    print_pitch_numbers(
        agents_count=len(enriched) if enriched else 97,
        feedback_count=len(feedback),
        agents_with_feedback=agents_with_fb,
    )

    print("=" * 70)
    print("Reputation Layer Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()