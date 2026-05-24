# Lumen

**AI Agent Trust Ratings for the Agentic Economy**

Bloomberg-style credit ratings for on-chain AI agents. Built on Mantle ERC-8004.

Built for [The Turing Test Hackathon 2026](https://dorahacks.io/hackathon/mantleturingtesthackathon2026).

---

## The Problem

The agentic economy is here — but its trust layer is being gamed.

Lumen scanned every AI agent on Mantle's ERC-8004 registry and found:

- **91.8%** of agents are sybil clones controlled by a single wallet
- **99%** of on-chain reputation signals come from a single self-feedback wallet
- **Zero** independent rating infrastructure exists

Investors are flying blind. Lumen is the trust layer they need.

---

## What Lumen Does

Lumen rates every on-chain AI agent across 5 dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| Completeness | 25% | Metadata quality (name, description, endpoints) |
| Capability | 25% | Skills, tools, integration depth |
| Owner Reputation | 20% | Sybil detection, wallet patterns |
| Verifiability | 15% | External proofs, schema compliance |
| Activity | 15% | On-chain feedback signals (penalized for self-feedback) |

Each agent gets a **0-100 Lumen Score** and a **Trust Status** (Safe / Caution / High Risk).

---

## Architecture

┌─────────────────────────────────────────────────┐
│  Mantle ERC-8004 (IdentityRegistry + ReputationRegistry)  │
└──────────────────────┬──────────────────────────┘
│ (on-chain reads)
↓
┌─────────────────────────────────────────────────┐
│  Indexer Pipeline (Python + web3.py)           │
│  - Agent indexer                                │
│  - Metadata decoder (base64 / gzip / IPFS)     │
│  - Sybil cluster detector                       │
│  - Reputation indexer                           │
└──────────────────────┬──────────────────────────┘
│
↓
┌─────────────────────────────────────────────────┐
│  Scoring Engine + Claude Analyst Agent         │
│  → Lumen Score + institutional-grade notes      │
└──────────────────────┬──────────────────────────┘
│
↓
┌─────────────────────────────────────────────────┐
│  FastAPI + Next.js Frontend                    │
│  Bloomberg-style trust ratings dashboard       │
└─────────────────────────────────────────────────┘

---

## Tech Stack

- **Backend:** Python, FastAPI, web3.py, Anthropic Claude API
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS
- **Smart Contracts:** Solidity, Foundry (coming Week 3)
- **Chain:** Mantle Mainnet, ERC-8004

---

## Current Status

**Phase:** Backend + Frontend skeleton complete · Day 5 of 25

- [x] Index 97 agents from Mantle ERC-8004 IdentityRegistry
- [x] Detect sybil clusters (91.8% of agents flagged)
- [x] Index 295 reputation signals from ReputationRegistry
- [x] 5-dimension scoring algorithm
- [x] FastAPI backend with rate limiting + input validation
- [x] Next.js frontend (rankings + detail pages)
- [ ] Claude analyst commentary (in progress)
- [ ] LumenScoringRegistry.sol on Mantle Mainnet
- [ ] UI/UX polish (with Chris)
- [ ] Demo video + Pitch deck

---

## Mantle ERC-8004 Contract Addresses

- **IdentityRegistry:** `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`
- **ReputationRegistry:** `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`

---

## Run Locally

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your ANTHROPIC_API_KEY
python scripts/pipeline.py   # index + score all agents
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Team

- **Amanda** — Engineering (backend, indexing, scoring, frontend skeleton)
- **Chris** — Product / UX (trust presentation, onboarding flow)

---

## License