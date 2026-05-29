"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

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
  analyst_note: string | null;
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
const CONTRACT_ADDRESS = "0x4ef1AD7f49254faA0398F7201E786ec47514de7C";
const EXPLORER_BASE = "https://sepolia.mantlescan.xyz";

function trustStatus(risk: string, score: number) {
  if (risk === "SYBIL") {
    return { label: "HIGH RISK", color: "text-red-400", bg: "bg-red-950/50 border-red-900" };
  }
  if (risk === "SUSPICIOUS") {
    return { label: "CAUTION", color: "text-yellow-400", bg: "bg-yellow-950/50 border-yellow-900" };
  }
  if (score < 30) {
    return { label: "CAUTION", color: "text-yellow-400", bg: "bg-yellow-950/50 border-yellow-900" };
  }
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
      .then((r) => {
        if (!r.ok) throw new Error(`Agent #${agentId} not found`);
        return r.json();
      })
      .then((data) => {
        setAgent(data);
        setLoading(false);
      })
      .catch((err) => {
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
            <Link href="/" className="text-zinc-400 hover:text-zinc-100 underline">Back to rankings</Link>
          </div>
        </div>
      </div>
    );
  }

  const status = trustStatus(agent.risk_level, agent.lumen_score);
  const explorerUrl = `${EXPLORER_BASE}/address/${CONTRACT_ADDRESS}#readContract`;
  const badgeClass = "inline-flex items-center gap-2 mt-3 px-3 py-1.5 border border-emerald-900 bg-emerald-950 rounded text-xs text-emerald-300 hover:bg-emerald-900 transition-colors";

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-mono">
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-baseline gap-4">
          <Link href="/" className="text-xl font-bold tracking-tight hover:text-zinc-300">LUMEN</Link>
          <span className="text-zinc-500 text-sm">/ Agent #{agent.agent_id}</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        <section className={`border rounded p-6 ${status.bg}`}>
          <div className="flex items-baseline justify-between flex-wrap gap-4">
            <div>
              <div className={`text-xs tracking-widest ${status.color} mb-1`}>TRUST STATUS</div>
              <div className={`text-3xl font-bold ${status.color}`}>{status.label}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-zinc-500 tracking-widest mb-1">LUMEN SCORE</div>
              <div className="text-4xl font-bold text-zinc-100">
                {agent.lumen_score}
                <span className="text-zinc-500 text-2xl ml-2">/ 100</span>
              </div>
              <div className="text-sm text-zinc-400 mt-1">Grade {agent.grade}</div>
              <a href={explorerUrl} target="_blank" rel="noopener noreferrer" className={badgeClass}>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>ON-CHAIN VERIFIED | Mantle Sepolia</span>
              </a>
            </div>
          </div>

          {agent.cluster_evidence && agent.cluster_evidence.length > 0 && (
            <div className="mt-6 pt-6 border-t border-red-900">
              <div className="text-xs text-red-400 tracking-widest mb-2">RISK EVIDENCE</div>
              <ul className="space-y-1 text-sm text-red-300">
                {agent.cluster_evidence.map((evidence, i) => (
                  <li key={i}>- {evidence}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {agent.analyst_note && (
          <section className="border border-zinc-800 rounded p-6 bg-zinc-900">
            <div className="text-xs text-zinc-500 tracking-widest mb-3">LUMEN ANALYST NOTE</div>
            <p className="text-zinc-200 leading-relaxed text-sm italic">{agent.analyst_note}</p>
          </section>
        )}

        <section className="border border-zinc-800 rounded p-6">
          <div className="text-xs text-zinc-500 tracking-widest mb-3">AGENT</div>
          <div className="text-2xl text-zinc-100 mb-2">{agent.name || "(unnamed)"}</div>
          <div className="text-sm text-zinc-400 leading-relaxed">{agent.description || "(no description)"}</div>

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

        <section className="border border-zinc-800 rounded p-6">
          <div className="text-xs text-zinc-500 tracking-widest mb-4">SCORE BREAKDOWN</div>
          <div className="grid md:grid-cols-2 gap-6 items-center">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={[
                  { dimension: "Completeness", value: agent.breakdown.completeness },
                  { dimension: "Capability", value: agent.breakdown.capability },
                  { dimension: "Owner Rep.", value: agent.breakdown.owner_reputation },
                  { dimension: "Verifiability", value: agent.breakdown.verifiability },
                  { dimension: "Activity", value: agent.breakdown.activity },
                ]}>
                  <PolarGrid stroke="#3f3f46" />
                  <PolarAngleAxis dataKey="dimension" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#52525b", fontSize: 10 }} tickCount={6} />
                  <Radar name="Score" dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-3">
              {Object.entries(agent.breakdown).map(([key, value]) => (
                <div key={key}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-zinc-400 capitalize">{key.replace("_", " ")}</span>
                    <span className="text-zinc-100">{value} / 100</span>
                  </div>
                  <div className="h-1 bg-zinc-900 rounded overflow-hidden">
                    <div className="h-full bg-emerald-500" style={{ width: `${value}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

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
                  <span className="text-zinc-100">{agent.reputation.avg_score.toFixed(2)}</span>
                </div>
              )}
              {agent.reputation.unique_client_count <= 1 && (
                <div className="text-yellow-400 text-xs mt-3 pt-3 border-t border-zinc-800">
                  All feedback from a single client - possible self-feedback
                </div>
              )}
            </div>
          ) : (
            <div className="text-zinc-500 text-sm">No on-chain feedback yet</div>
          )}
        </section>

        <Link href="/" className="inline-block text-zinc-400 hover:text-zinc-100 text-sm">Back to rankings</Link>
      </main>
    </div>
  );
}