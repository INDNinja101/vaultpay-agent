"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import AuditTimeline from "../../components/AuditTimeline";

export default function AuditPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [taskId, setTaskId] = useState("");
  function load() {
    const q = taskId ? `?task_id=${taskId}` : "";
    api(`/api/audit${q}`).then((d) => setEvents(d.events)).catch(() => {});
  }
  useEffect(load, [taskId]);
  async function reset() { await api("/api/demo/reset", { method: "POST", body: "{}" }); load(); }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Money timeline — every dollar, explained</h1>
      <div className="flex gap-3 items-center">
        <input className="input" style={{ maxWidth: 180 }} placeholder="Filter by task #" value={taskId} onChange={(e) => setTaskId(e.target.value)} />
        <button className="btn btn-danger" onClick={reset}>Reset demo</button>
      </div>
      <AuditTimeline events={events} />
    </div>
  );
}
