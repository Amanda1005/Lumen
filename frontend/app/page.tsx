"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
} from "recharts";

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

type GradeDistribution = {
  distribution: { grade: string; count: number; percent: number }[];
  total: number;
};

type RiskFilter = "ALL" | "SAFE" | "SUSPICIOUS" | "SYBIL";
type SortKey = "score_desc" | "score_asc" | "id_asc";

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
  const [agents, setAgents] = useState<Agent[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [distribution, setDistribution] = useState<GradeDistribution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("score_desc");

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/stats`).then(r => r.json()),
      fetch(`${API_BASE}/api/agents?limit=500`).then(r => r.json()),
      fetch(`${API_BASE}/api/grade-distribution`).then(r => r.json()),
    ])
      .then(([statsData, agentsData, distData]) => {
        setStats(statsData);
        setAgents(agentsData.agents);
        setDistribution(distData);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Filtered + sorted agents
  const filteredAgents = useMemo(() => {
    let result = [...agents];

    if (riskFilter !== "ALL") {
      result = result.filter(a => a.risk_level === riskFilter);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        a =>
          a.name.toLowerCase().includes(q) ||
          a.owner.toLowerCase().includes(q) ||
          a.agent_id.toString().includes(q)
      );
    }

    if (sortKey === "score_desc")
      result.sort((a, b) => b.lumen_score - a.lumen_score);
    else if (sortKey === "score_asc")
      result.sort((a, b) => a.lumen_score - b.lumen_score);
    else if (sortKey === "id_asc")
      result.sort((a, b) => a.agent_id - b.agent_id);

    return result;
  }, [agents, riskFilter, search, sortKey]);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center font-mono">
        <div className="text-zinc-400">Loading agents...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center font-mono">
        <div className="text-red-400">
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
        <div className="max-w-6xl mx-auto flex items-baseline justify-between flex-wrap gap-4">
          <div className="flex items-baseline gap-4">
            <h1 className="text-2xl font-bold tracking-tight">LUMEN</h1>
            <span className="text-zinc-500 text-sm">
              AI Agent Trust Ratings · Mantle Mainnet
            </span>
          </div>
          <nav className="flex gap-4 text-sm">
            <Link href="/" className="text-zinc-100 hover:text-zinc-300">
              Rankings
            </Link>
            <Link href="/alerts" className="text-zinc-400 hover:text-zinc-100">
              Alerts
            </Link>
          </nav>
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

      {/* Grade distribution chart */}
      {distribution && (
        <div className="border-b border-zinc-800 px-6 py-6 bg-zinc-950">
          <div className="max-w-6xl mx-auto">
            <div className="text-xs text-zinc-500 tracking-widest mb-4">
              GRADE DISTRIBUTION · ECOSYSTEM HEALTH
            </div>
            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={distribution.distribution}
                  margin={{ top: 10, right: 0, left: -30, bottom: 0 }}
                >
                  <XAxis
                    dataKey="grade"
                    tick={{ fill: "#a1a1aa", fontSize: 12 }}
                    axisLine={{ stroke: "#3f3f46" }}
                  />
                  <YAxis
                    tick={{ fill: "#52525b", fontSize: 11 }}
                    axisLine={{ stroke: "#3f3f46" }}
                  />
                  <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                    {distribution.distribution.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={
                          entry.grade === "A" || entry.grade === "B"
                            ? "#10b981"
                            : entry.grade === "C"
                            ? "#eab308"
                            : "#ef4444"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex gap-6 mt-3 text-xs text-zinc-500 flex-wrap">
              {distribution.distribution.map(d => (
                <div key={d.grade}>
                  <span className="text-zinc-400">{d.grade}: </span>
                  <span className="text-zinc-100">{d.count}</span>
                  <span className="text-zinc-600"> ({d.percent}%)</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="border-b border-zinc-800 px-6 py-4 bg-zinc-950">
        <div className="max-w-6xl mx-auto flex flex-wrap gap-4 items-center">
          <input
            type="text"
            placeholder="Search by name, owner, or ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 min-w-64 bg-zinc-900 border border-zinc-800 rounded px-3 py-2 text-sm
                       text-zinc-100 placeholder-zinc-600 focus:outline-none
                       focus:border-zinc-600"
          />

          <div className="flex gap-1">
            {(["ALL", "SAFE", "SUSPICIOUS", "SYBIL"] as RiskFilter[]).map(r => (
              <button
                key={r}
                onClick={() => setRiskFilter(r)}
                className={`px-3 py-2 text-xs tracking-widest border rounded transition-colors ${
                  riskFilter === r
                    ? r === "SYBIL"
                      ? "bg-red-950/50 border-red-900 text-red-300"
                      : r === "SAFE"
                      ? "bg-emerald-950/50 border-emerald-900 text-emerald-300"
                      : r === "SUSPICIOUS"
                      ? "bg-yellow-950/50 border-yellow-900 text-yellow-300"
                      : "bg-zinc-800 border-zinc-700 text-zinc-100"
                    : "border-zinc-800 text-zinc-500 hover:text-zinc-300 hover:border-zinc-700"
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <select
            value={sortKey}
            onChange={e => setSortKey(e.target.value as SortKey)}
            className="bg-zinc-900 border border-zinc-800 rounded px-3 py-2 text-sm
                       text-zinc-100 focus:outline-none focus:border-zinc-600 cursor-pointer"
          >
            <option value="score_desc">Score: High → Low</option>
            <option value="score_asc">Score: Low → High</option>
            <option value="id_asc">Agent ID</option>
          </select>
        </div>

        <div className="max-w-6xl mx-auto mt-3 text-xs text-zinc-500">
          Showing {filteredAgents.length} of {agents.length} agents
        </div>
      </div>

      {/* Table */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {filteredAgents.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">
            No agents match your filters.
          </div>
        ) : (
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
              {filteredAgents.map((agent, i) => (
                <tr
                  key={agent.agent_id}
                  className="border-b border-zinc-900 hover:bg-zinc-900/50 transition-colors cursor-pointer"
                  onClick={() =>
                    (window.location.href = `/agents/${agent.agent_id}`)
                  }
                >
                  <td className="py-2 pr-4 text-zinc-500">{i + 1}</td>
                  <td className="py-2 pr-4 text-zinc-500">#{agent.agent_id}</td>
                  <td className="py-2 pr-4 text-zinc-100">{agent.name}</td>
                  <td className="py-2 pr-4 text-zinc-100">
                    {agent.lumen_score}
                  </td>
                  <td
                    className={`py-2 pr-4 font-bold ${gradeColor(agent.grade)}`}
                  >
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
        )}
      </main>
    </div>
  );
}