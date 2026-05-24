"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Agent = {
  agent_id: number;
  name: string;
  owner: string;
  lumen_score: number;
  grade: string;
  risk_level: string;
  breakdown: {
    completeness: number;
    capability: number;
    owner_reputation: number;
    verifiability: number;
    activity: number;
  };
};

type Stats = {
  total_agents: number;
  safe: number;
  sybil: number;
  avg_score: number;
};

const API_BASE = "http://localhost:8000";

function riskColor(risk: string): string {
  if (risk === "SAFE") return "text-emerald-400";
  if (risk === "SYBIL") return "text-red-400";
  return "text-yellow-400";
}

function gradeColor(grade: string): string {
  if (grade === "A" || grade === "B") return "text-emerald-400";
  if (grade === "C") return "text-yellow-400";
  return "text-red-400";
}

export default function Home() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/stats`).then(r => r.json()),
      fetch(`${API_BASE}/api/agents?limit=100`).then(r => r.json()),
    ])
      .then(([statsData, agentsData]) => {
        setStats(statsData);
        setAgents(agentsData.agents);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center">
        <div className="text-zinc-400 font-mono">Loading agents...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center">
        <div className="text-red-400 font-mono">
          Error: {error}
          <div className="text-zinc-500 text-sm mt-2">
            Make sure the API is running on {API_BASE}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-mono">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-baseline gap-4">
          <h1 className="text-2xl font-bold tracking-tight">LUMEN</h1>
          <span className="text-zinc-500 text-sm">
            AI Agent Trust Ratings · Mantle Mainnet
          </span>
        </div>
      </header>

      {/* Stats bar */}
      {stats && (
        <div className="border-b border-zinc-800 bg-zinc-900/50 px-6 py-3">
          <div className="max-w-6xl mx-auto flex gap-8 text-sm">
            <div>
              <span className="text-zinc-500">Total: </span>
              <span className="text-zinc-100">{stats.total_agents}</span>
            </div>
            <div>
              <span className="text-zinc-500">Safe: </span>
              <span className="text-emerald-400">{stats.safe}</span>
            </div>
            <div>
              <span className="text-zinc-500">Sybil: </span>
              <span className="text-red-400">{stats.sybil}</span>
            </div>
            <div>
              <span className="text-zinc-500">Avg score: </span>
              <span className="text-zinc-100">{stats.avg_score}</span>
            </div>
          </div>
        </div>
      )}

      {/* Sybil alert banner */}
      {stats && stats.sybil > 0 && (
        <div className="bg-red-950/40 border-b border-red-900/50 px-6 py-3">
          <div className="max-w-6xl mx-auto text-sm text-red-300">
            ⚠️ Lumen detected{" "}
            <span className="font-bold">
              {((stats.sybil / stats.total_agents) * 100).toFixed(1)}%
            </span>{" "}
            sybil clones from a single wallet. Filter risk to inspect.
          </div>
        </div>
      )}

      {/* Table */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-500 text-left">
              <th className="py-2 pr-4 font-normal">#</th>
              <th className="py-2 pr-4 font-normal">ID</th>
              <th className="py-2 pr-4 font-normal">Name</th>
              <th className="py-2 pr-4 font-normal">Score</th>
              <th className="py-2 pr-4 font-normal">Grade</th>
              <th className="py-2 pr-4 font-normal">Risk</th>
              <th className="py-2 pr-4 font-normal">Owner</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent, i) => (
              <tr
                key={agent.agent_id}
                className="border-b border-zinc-900 hover:bg-zinc-900/50 transition-colors cursor-pointer"
                onClick={() => router.push(`/agents/${agent.agent_id}`)}
              >
                <td className="py-2 pr-4 text-zinc-500">{i + 1}</td>
                <td className="py-2 pr-4 text-zinc-500">#{agent.agent_id}</td>
                <td className="py-2 pr-4 text-zinc-100">{agent.name}</td>
                <td className="py-2 pr-4 text-zinc-100">{agent.lumen_score}</td>
                <td className={`py-2 pr-4 font-bold ${gradeColor(agent.grade)}`}>
                  {agent.grade}
                </td>
                <td className={`py-2 pr-4 ${riskColor(agent.risk_level)}`}>
                  {agent.risk_level}
                </td>
                <td className="py-2 pr-4 text-zinc-500 text-xs">
                  {agent.owner.slice(0, 6)}...{agent.owner.slice(-4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </main>
    </div>
  );
}