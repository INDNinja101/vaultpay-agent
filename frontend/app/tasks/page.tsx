"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import TaskTracker from "../../components/TaskTracker";

const EXAMPLES = [
  "Buy the Complete Fest Decoration Kit for the fest",
  "Buy LED String Lights 10m",
  "Buy Premium Gift Hamper",
  "Buy a streaming subscription",
];

export default function TasksPage() {
  const [prompt, setPrompt] = useState(EXAMPLES[0]);
  const [task, setTask] = useState<any>(null);
  const [err, setErr] = useState("");
  const timer = useRef<any>(null);

  async function run() {
    setErr("");
    try {
      const d = await api("/api/tasks", { method: "POST", body: JSON.stringify({ prompt }) });
      await refresh(d.task_id);
      // live tracker: poll every 2s a few times (status changes after approvals)
      let n = 0;
      clearInterval(timer.current);
      timer.current = setInterval(async () => { n++; await refresh(d.task_id); if (n > 5) clearInterval(timer.current); }, 2000);
    } catch (e: any) { setErr(String(e.message || e)); }
  }
  async function refresh(id: number) { try { setTask(await api(`/api/tasks/${id}`)); } catch {} }
  useEffect(() => () => clearInterval(timer.current), []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Ask the agent to buy something</h1>
      <input className="input" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
      <div className="flex flex-wrap gap-2">{EXAMPLES.map((x) => (
        <button key={x} className="text-xs bg-gray-800 px-2 py-1 rounded" onClick={() => setPrompt(x)}>{x}</button>))}
      </div>
      <button className="btn" onClick={run}>Run task</button>
      {err && <p className="text-red-400 text-sm">{err} — is the backend running on :8000?</p>}
      <TaskTracker task={task} />
    </div>
  );
}
