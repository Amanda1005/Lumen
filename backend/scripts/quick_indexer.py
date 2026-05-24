"""
Quick Indexer - Lumen

Goal: Connect to Mantle Mainnet, scan Transfer events from ERC-8004
IdentityRegistry, and list all registered AI agents.

Why events instead of totalSupply():
The IdentityRegistry is a basic ERC-721 (not Enumerable), so we can't
iterate by index. Instead, we scan the Transfer event from address(0),
which represents mints (i.e., agent registrations).
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# ============================================================
# Configuration
# ============================================================

MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
IDENTITY_REGISTRY_ADDRESS = os.getenv("IDENTITY_REGISTRY_ADDRESS")

# Contract deployed ~95 days ago. From the screenshot we know
# the first Register tx is around block 92.2M. We start a bit earlier
# to be safe and scan forward.
DEPLOY_BLOCK = 91_000_000  # Approximate deployment block
CHUNK_SIZE = 10_000  # Blocks per query (Mantle RPC limit)

# Minimal ABI - only what we need
IDENTITY_REGISTRY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": True, "name": "tokenId", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


# ============================================================
# Indexer
# ============================================================

def connect_to_mantle() -> Web3:
    """Connect to Mantle Mainnet and verify the connection."""
    print(f"Connecting to Mantle Mainnet: {MANTLE_RPC_URL}")
    w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL))

    if not w3.is_connected():
        raise ConnectionError("Failed to connect to Mantle RPC")

    chain_id = w3.eth.chain_id
    block_number = w3.eth.block_number
    print(f"Connected. Chain ID: {chain_id}, Latest block: {block_number}\n")
    return w3


def get_identity_registry(w3: Web3):
    """Load the ERC-8004 IdentityRegistry contract."""
    address = Web3.to_checksum_address(IDENTITY_REGISTRY_ADDRESS)
    contract = w3.eth.contract(address=address, abi=IDENTITY_REGISTRY_ABI)
    print(f"IdentityRegistry loaded at: {address}\n")
    return contract


def scan_mint_events(w3: Web3, contract, from_block: int, to_block: int) -> list[int]:
    """
    Scan Transfer events where `from` = zero address (i.e., mints).
    Returns a list of unique agent IDs that have been registered.
    """
    print(f"Scanning blocks {from_block:,} to {to_block:,} for mint events...")
    print(f"   Chunk size: {CHUNK_SIZE:,} blocks per query\n")

    agent_ids = set()
    current = from_block
    chunk_count = 0

    while current <= to_block:
        end = min(current + CHUNK_SIZE - 1, to_block)
        chunk_count += 1

        try:
            # Filter: Transfer event from zero address (= mint)
            event_filter = contract.events.Transfer.create_filter(
                from_block=current,
                to_block=end,
                argument_filters={"from": ZERO_ADDRESS},
            )
            events = event_filter.get_all_entries()

            if events:
                for event in events:
                    token_id = event["args"]["tokenId"]
                    agent_ids.add(token_id)

                print(f"   Blocks {current:,}-{end:,}: found {len(events)} mints "
                      f"(total unique agents so far: {len(agent_ids)})")

        except Exception as e:
            print(f"   Blocks {current:,}-{end:,}: skipped ({type(e).__name__})")

        current = end + 1

    print(f"\nScanned {chunk_count} chunks. Found {len(agent_ids)} unique agents.\n")
    return sorted(agent_ids)


def fetch_agent_details(contract, agent_ids: list[int]) -> list[dict]:
    """For each agent ID, fetch owner and tokenURI."""
    agents = []
    print("Fetching agent details (owner + tokenURI)...")
    print("-" * 70)

    for i, agent_id in enumerate(agent_ids):
        try:
            owner = contract.functions.ownerOf(agent_id).call()

            try:
                token_uri = contract.functions.tokenURI(agent_id).call()
            except Exception:
                token_uri = "(not set)"

            agents.append({
                "agent_id": agent_id,
                "owner": owner,
                "token_uri": token_uri,
            })

            if (i + 1) % 10 == 0 or i == len(agent_ids) - 1:
                print(f"   Progress: {i + 1}/{len(agent_ids)} agents detailed")

        except Exception as e:
            print(f"   Failed for agent #{agent_id}: {e}")

    print("-" * 70)
    print(f"Successfully fetched details for {len(agents)} agents\n")
    return agents


def save_to_json(agents: list[dict], output_path: str = "data/agents.json"):
    """Save indexed agents to JSON for downstream use."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w") as f:
        json.dump(agents, f, indent=2)

    print(f"Saved {len(agents)} agents to: {output.resolve()}")


def print_sample(agents: list[dict], n: int = 5):
    """Show first N agents as a sanity check."""
    print(f"\nSample of first {n} agents:\n")
    for agent in agents[:n]:
        uri = agent["token_uri"]
        uri_display = uri[:80] + "..." if len(uri) > 80 else uri
        print(f"   Agent #{agent['agent_id']}")
        print(f"      Owner: {agent['owner']}")
        print(f"      URI:   {uri_display}")
        print()


# ============================================================
# Entry Point
# ============================================================

def main():
    print("=" * 70)
    print("Lumen Quick Indexer (v2 - Event-based)")
    print("=" * 70 + "\n")

    w3 = connect_to_mantle()
    contract = get_identity_registry(w3)

    latest_block = w3.eth.block_number
    agent_ids = scan_mint_events(w3, contract, DEPLOY_BLOCK, latest_block)

    if not agent_ids:
        print("No agents found. Check DEPLOY_BLOCK or contract address.")
        return

    agents = fetch_agent_details(contract, agent_ids)
    save_to_json(agents)
    print_sample(agents, n=5)

    print("=" * 70)
    print(f"Day 1 Complete! Indexed {len(agents)} agents from Mantle Mainnet.")
    print("=" * 70)


if __name__ == "__main__":
    main()