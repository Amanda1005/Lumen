"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Agent = {
  agent_id: number;
  name: string;
  owner: string;
  lumen_score: number;
  grade: string;
  risk_level: string;
};

type Stats = {
  total_agents: number;
  safe: number;
  sybil: number;
  avg_score: number;
};

const API_BASE = "http://localhost:8000";

export default function AlertsPage() {
  const [sybilAgents, setSybilAgents] = useState<Agent[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/stats`).then(r => r.json()),
      fetch(`${API_BASE}/api/agents?risk=SYBIL&limit=500`).then(r => r.json()),
    ])
      .then(([statsData, agentsData]) => {
        setStats(statsData);
        setSybilAgents(agentsData.agents);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center font-mono">
        <div className="text-zinc-400">Loading alerts...</div>
      </div>
    );
  }

  const ownerGroups: Record<string, Agent[]> = {};
  sybilAgents.forEach(a => {
    if (!ownerGroups[a.owner]) ownerGroups[a.owner] = [];
    ownerGroups[a.owner].push(a);
  });

  const sybilPercent = stats
    ? ((stats.sybil / stats.total_agents) * 100).toFixed(1)
    : "0";

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-mono">
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-baseline gap-4">
          <Link href="/" className="text-xl font-bold tracking-tight hover:text-zinc-300">
            LUMEN
          </Link>
          <span className="text-zinc-500 text-sm">/ Scam Alerts</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        <section className="border border-red-900 rounded p-8 bg-red-950/40">
          <div className="text-xs tracking-widest text-red-400 mb-2">
            ACTIVE SCAM ALERT - MANTLE MAINNET
          </div>
          <h1 className="text-4xl font-bold text-red-300 mb-4">
            {sybilPercent}% Sybil Attack Detected
          </h1>
          <p className="text-zinc-300 leading-relaxed">
            Lumen has identified a coordinated sybil attack on Mantle ERC-8004
            ecosystem.{" "}
            <span className="text-red-400 font-bold">
              {stats?.sybil} cloned agents
            </span>{" "}
            from a single wallet are flooding the registry with identical
            arbitrage bot listings, designed to mislead investors.
          </p>
        </section>

        <section className="border border-zinc-800 rounded p-6">
          <div className="text-xs text-zinc-500 tracking-widest mb-4">
            BY THE NUMBERS
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <Metric label="Total agents scanned" value={stats?.total_agents || 0} />
            <Metric label="Sybil clones" value={stats?.sybil || 0} highlight="red" />
            <Metric label="Unique attackers" value={Object.keys(ownerGroups).length} />
            <Metric label="Safe agents" value={stats?.safe || 0} highlight="green" />
          </div>
        </section>

        {Object.entries(ownerGroups).map(([owner, agents]) => (
          <section
            key={owner}
            className="border border-red-900/50 rounded p-6 bg-red-950/20"
          >
            <div className="text-xs text-red-400 tracking-widest mb-3">
              ATTACKER WALLET
            </div>
            <div className="text-zinc-100 break-all mb-4 text-sm">
              <a
                href={`https://mantlescan.xyz/address/${owner}`}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-red-300 underline decoration-zinc-700"
              >
                {owner}
              </a>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
              <div>
                <div className="text-zinc-500 text-xs">CLONES MINTED</div>
                <div className="text-red-300 text-2xl font-bold">
                  {agents.length}
                </div>
              </div>
              <div>
                <div className="text-zinc-500 text-xs">AVG LUMEN SCORE</div>
                <div className="text-red-300 text-2xl font-bold">
                  {Math.round(
                    agents.reduce((s, a) => s + a.lumen_score, 0) / agents.length
                  )}
                  <span className="text-zinc-500 text-sm"> / 100</span>
                </div>
              </div>
            </div>

            <div className="text-xs text-zinc-500 tracking-widest mb-2">
              EVIDENCE
            </div>
            <ul className="space-y-1 text-sm text-red-300 mb-4">
              <li>- Sequential naming pattern (babycaisubagent-001 to 102)</li>
              <li>- Identical descriptions across {agents.length} agents</li>
              <li>- Mass registration in under 1 hour window</li>
              <li>- Missing IDs suggest bot automation, not manual minting</li>
            </ul>

            <details className="mt-4">
              <summary className="text-zinc-400 text-xs cursor-pointer hover:text-zinc-200">
                View all {agents.length} clones
              </summary>
              <div className="mt-3 max-h-96 overflow-y-auto border border-zinc-800 rounded">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-zinc-900">
                    <tr className="text-zinc-500 text-left">
                      <th className="px-3 py-2 font-normal">ID</th>
                      <th className="px-3 py-2 font-normal">Name</th>
                      <th className="px-3 py-2 font-normal">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.map(a => (
                      <tr
                        key={a.agent_id}
                        className="border-t border-zinc-900 hover:bg-zinc-900/50 cursor-pointer"
                        onClick={() => (window.location.href = `/agents/${a.agent_id}`)}
                      >
                        <td className="px-3 py-2 text-zinc-500">#{a.agent_id}</td>
                        <td className="px-3 py-2 text-zinc-300">{a.name}</td>
                        <td className="px-3 py-2 text-red-400">{a.lumen_score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </section>
        ))}

        <Link
          href="/"
          className="inline-block text-zinc-400 hover:text-zinc-100 text-sm"
        >
          Back to rankings
        </Link>
      </main>
    </div>
  );
}

function Metric({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number | string;
  highlight?: "red" | "green";
}) {
  const colorClass =
    highlight === "red"
      ? "text-red-400"
      : highlight === "green"
      ? "text-emerald-400"
      : "text-zinc-100";

  return (
    <div>
      <div className="text-zinc-500 text-xs tracking-widest mb-1">{label}</div>
      <div className={`text-3xl font-bold ${colorClass}`}>{value}</div>
    </div>
  );
}