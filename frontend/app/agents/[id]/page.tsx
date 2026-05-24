"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

type Agent = {
  agent_id: number;
  name: string;
  owner: string;
  uri_type: string;
  description: string;
  risk_level: string;
  cluster_size: number;
  cluster_evidence: string[];
  lumen_score: number;
  grade: string;
  breakdown: {
    completeness: number;
    capability: number;
    owner_reputation: number;
    verifiability: number;
    activity: number;
  };
  reputation: {
    feedback_count: number;
    unique_client_count: number;
    avg_score: number | null;
    top_tags: [string, number][];
  };
  raw_metadata: Record<string, unknown> | null;
};

const API_BASE = "http://localhost:8000";

function trustStatus(risk: string, score: number) {
  if (risk === "SYBIL") return { label: "HIGH RISK", color: "text-red-400", bg: "bg-red-950/50 border-red-900" };
  if (risk === "SUSPICIOUS") return { label: "CAUTION", color: "text-yellow-400", bg: "bg-yellow-950/50 border-yellow-900" };
  if (score < 30) return { label: "CAUTION", color: "text-yellow-400", bg: "bg-yellow-950/50 border-yellow-900" };
  return { label: "SAFE", color: "text-emerald-400", bg: "bg-emerald-950/50 border-emerald-900" };
}

export default function AgentDetailPage() {
  const params = useParams();
  const agentId = params.id;

  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/agents/${agentId}`)
      .then(r => {
        if (!r.ok) throw new Error(`Agent #${agentId} not found`);
        return r.json();
      })
      .then(data => {
        setAgent(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [agentId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center font-mono">
        <div className="text-zinc-400">Loading agent...</div>
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center font-mono">
        <div className="text-red-400">
          {error || "Agent not found"}
          <div className="mt-4">
            <Link href="/" className="text-zinc-400 hover:text-zinc-100 underline">
              ← Back to rankings
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const status = trustStatus(agent.risk_level, agent.lumen_score);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-mono">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-baseline gap-4">
          <Link href="/" className="text-xl font-bold tracking-tight hover:text-zinc-300">
            LUMEN
          </Link>
          <span className="text-zinc-500 text-sm">/ Agent #{agent.agent_id}</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Trust Status - the hero block */}
        <section className={`border rounded p-6 ${status.bg}`}>
          <div className="flex items-baseline justify-between flex-wrap gap-4">
            <div>
              <div className={`text-xs tracking-widest ${status.color} mb-1`}>
                TRUST STATUS
              </div>
              <div className={`text-3xl font-bold ${status.color}`}>
                {status.label}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-zinc-500 tracking-widest mb-1">LUMEN SCORE</div>
              <div className="text-4xl font-bold text-zinc-100">
                {agent.lumen_score}
                <span className="text-zinc-500 text-2xl ml-2">/ 100</span>
              </div>
              <div className="text-sm text-zinc-400 mt-1">Grade {agent.grade}</div>
            </div>
          </div>

          {/* Risk evidence */}
          {agent.cluster_evidence && agent.cluster_evidence.length > 0 && (
            <div className="mt-6 pt-6 border-t border-red-900/50">
              <div className="text-xs text-red-400 tracking-widest mb-2">⚠ RISK EVIDENCE</div>
              <ul className="space-y-1 text-sm text-red-300">
                {agent.cluster_evidence.map((evidence, i) => (
                  <li key={i}>• {evidence}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Agent Info */}
        <section className="border border-zinc-800 rounded p-6">
          <div className="text-xs text-zinc-500 tracking-widest mb-3">AGENT</div>
          <div className="text-2xl text-zinc-100 mb-2">{agent.name || "(unnamed)"}</div>
          <div className="text-sm text-zinc-400 leading-relaxed">
            {agent.description || "(no description)"}
          </div>

          <div className="grid grid-cols-2 gap-4 mt-6 text-sm">
            <div>
              <div className="text-zinc-500 text-xs">OWNER</div>
              <div className="text-zinc-300 break-all">{agent.owner}</div>
            </div>
            <div>
              <div className="text-zinc-500 text-xs">URI TYPE</div>
              <div className="text-zinc-300">{agent.uri_type}</div>
            </div>
          </div>
        </section>

        {/* Score Breakdown */}
        <section className="border border-zinc-800 rounded p-6">
          <div className="text-xs text-zinc-500 tracking-widest mb-4">SCORE BREAKDOWN</div>
          <div className="space-y-3">
            {Object.entries(agent.breakdown).map(([key, value]) => (
              <div key={key}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-zinc-400 capitalize">
                    {key.replace("_", " ")}
                  </span>
                  <span className="text-zinc-100">{value} / 100</span>
                </div>
                <div className="h-1 bg-zinc-900 rounded overflow-hidden">
                  <div
                    className="h-full bg-emerald-500"
                    style={{ width: `${value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Reputation */}
        <section className="border border-zinc-800 rounded p-6">
          <div className="text-xs text-zinc-500 tracking-widest mb-4">ON-CHAIN REPUTATION</div>
          {agent.reputation.feedback_count > 0 ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-500">Feedback count</span>
                <span className="text-zinc-100">{agent.reputation.feedback_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Unique clients</span>
                <span className="text-zinc-100">{agent.reputation.unique_client_count}</span>
              </div>
              {agent.reputation.avg_score !== null && (
                <div className="flex justify-between">
                  <span className="text-zinc-500">Avg score</span>
                  <span className="text-zinc-100">
                    {agent.reputation.avg_score.toFixed(2)}
                  </span>
                </div>
              )}
              {agent.reputation.unique_client_count <= 1 && (
                <div className="text-yellow-400 text-xs mt-3 pt-3 border-t border-zinc-800">
                  ⚠ All feedback from a single client — possible self-feedback
                </div>
              )}
            </div>
          ) : (
            <div className="text-zinc-500 text-sm">No on-chain feedback yet</div>
          )}
        </section>

        <Link
          href="/"
          className="inline-block text-zinc-400 hover:text-zinc-100 text-sm"
        >
          ← Back to rankings
        </Link>
      </main>
    </div>
  );
}