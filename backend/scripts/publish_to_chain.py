"""
Publish Lumen Scores to Mantle Sepolia LumenScoringRegistry.
Reads agents_with_comments.json, writes Lumen Score on-chain via batchUpdateScores.
"""

import json
import os
from hashlib import sha256
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

# ============================================================
# Configuration
# ============================================================

RPC_URL = os.getenv("MANTLE_SEPOLIA_RPC", "https://rpc.sepolia.mantle.xyz")
CONTRACT_ADDRESS = os.getenv("LUMEN_CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("SCORER_PRIVATE_KEY")

INPUT = Path("data/agents_with_comments.json")
BATCH_SIZE = 30  # contract limit is 50, we use 30 for safety

# Grade letter -> uint8
GRADE_MAP = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}
# Risk -> uint8 enum (SAFE=0, SUSPICIOUS=1, SYBIL=2)
RISK_MAP = {"SAFE": 0, "SUSPICIOUS": 1, "SYBIL": 2}

# Minimal ABI for batchUpdateScores
CONTRACT_ABI = [
    {
        "inputs": [
            {"name": "agentIds", "type": "uint256[]"},
            {"name": "scores", "type": "uint16[]"},
            {"name": "grades", "type": "uint8[]"},
            {"name": "risks", "type": "uint8[]"},
            {"name": "analysisURIs", "type": "string[]"},
            {"name": "analysisHashes", "type": "bytes32[]"},
        ],
        "name": "batchUpdateScores",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "scoredAgentCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def main():
    print("=" * 70)
    print("Publishing Lumen Scores to Mantle Sepolia")
    print("=" * 70 + "\n")

    if not PRIVATE_KEY or not CONTRACT_ADDRESS:
        print("Missing env vars. Check backend/.env")
        return

    # Setup
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("Failed to connect to Mantle Sepolia")
        return

    account = Account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=CONTRACT_ABI,
    )

    print(f"Network:  Mantle Sepolia (chainId 5003)")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Scorer:   {account.address}")
    print(f"Balance:  {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} MNT\n")

    # Load agents
    with open(INPUT) as f:
        agents = json.load(f)

    print(f"Publishing {len(agents)} agents in batches of {BATCH_SIZE}...\n")

    # Build calldata for each batch
    nonce = w3.eth.get_transaction_count(account.address)
    total_batches = (len(agents) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(agents))
        batch = agents[start:end]

        agent_ids = []
        scores = []
        grades = []
        risks = []
        uris = []
        hashes = []

        for a in batch:
            agent_ids.append(a["agent_id"])
            scores.append(int(a["lumen_score"]))
            grades.append(GRADE_MAP.get(a["grade"], 0))
            risks.append(RISK_MAP.get(a.get("risk_level", "SAFE"), 0))

            # Build URI: in production this would be IPFS, for demo we use a placeholder
            uri = f"lumen://agent/{a['agent_id']}"
            uris.append(uri)

            # Hash of analyst note (proves on-chain that the note hasn't been tampered)
            note = a.get("analyst_note") or ""
            note_hash = sha256(note.encode("utf-8")).digest()
            hashes.append(note_hash)

        # Build transaction
        print(f"[Batch {batch_idx + 1}/{total_batches}] agents {start}-{end-1}...")

        try:
            tx = contract.functions.batchUpdateScores(
                agent_ids, scores, grades, risks, uris, hashes
            ).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "gas": 5_000_000,
                "gasPrice": w3.eth.gas_price,
                "chainId": 5003,
            })

            signed = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"   Tx sent: {tx_hash.hex()}")
            print(f"   Waiting for confirmation...")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                print(f"   Confirmed in block {receipt.blockNumber}")
                print(f"   Gas used: {receipt.gasUsed:,}\n")
            else:
                print(f"   Transaction failed!\n")
                return

            nonce += 1

        except Exception as e:
            print(f"   Error: {e}\n")
            return

    # Verify
    on_chain_count = contract.functions.scoredAgentCount().call()
    print("=" * 70)
    print(f"Done. On-chain scored agents: {on_chain_count}")
    print(f"View on explorer: https://sepolia.mantlescan.xyz/address/{CONTRACT_ADDRESS}")
    print("=" * 70)


if __name__ == "__main__":
    main()