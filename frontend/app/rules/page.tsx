"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import PolicyPreview from "../../components/PolicyPreview";

export default function RulesPage() {
  const [text, setText] = useState("Fest supplies under $60, ask me above $25, never subscriptions, only sellers rated 4+");
  const [policy, setPolicy] = useState<any>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => { api("/api/policies/active").then((d) => setPolicy(d.policy_json)).catch(() => {}); }, []);

  async function parse() {
    const d = await api("/api/policies/parse", { method: "POST", body: JSON.stringify({ text }) });
    setPolicy(d.policy_json); setMsg("Parsed. Review the preview, then save.");
  }
  async function save() {
    const d = await api("/api/policies", { method: "POST", body: JSON.stringify({ policy_json: policy }) });
    setPolicy(d.policy_json); setMsg(`Saved as active policy v${d.version}. The engine now enforces exactly this.`);
  }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Your spending rules — in plain language</h1>
      <p className="text-gray-400 text-sm">The AI parses this into a strict policy. After that, only deterministic code decides if money moves.</p>
      <textarea className="input" rows={3} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="flex gap-3">
        <button className="btn" onClick={parse}>Parse rules</button>
        <button className="btn" onClick={save} disabled={!policy}>Save as active policy</button>
      </div>
      {msg && <p className="text-green-400 text-sm">{msg}</p>}
      <PolicyPreview policy={policy} />
    </div>
  );
}
