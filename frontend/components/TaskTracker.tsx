const BADGE: Record<string, string> = {
  ALLOW: "bg-green-900 text-green-300", ASK: "bg-yellow-900 text-yellow-300",
  DENY: "bg-red-900 text-red-300", PAID: "bg-green-800 text-green-200",
  PENDING_APPROVAL: "bg-yellow-800 text-yellow-200", DENIED: "bg-red-800 text-red-200",
};

export default function TaskTracker({ task }: { task: any }) {
  if (!task) return null;
  return (
    <div className="card space-y-3">
      <div className="flex justify-between">
        <span className="font-bold">Task #{task.id} — {task.status}</span>
        <span>Spent: <b>${Number(task.spent_total || 0).toFixed(2)}</b></span>
      </div>
      <p className="text-sm text-gray-400">&quot;{task.prompt}&quot;</p>
      {task.summary && <p className="text-sm">{task.summary}</p>}
      <div className="space-y-2">
        {(task.candidates || []).map((c: any) => (
          <div key={c.id} className="flex items-start justify-between gap-3 bg-black/30 rounded p-3">
            <div>
              <div className="font-semibold">{c.item?.name} — ${Number(c.item?.price || 0).toFixed(2)}</div>
              <div className="text-xs text-gray-400">{c.justification}</div>
              <div className="text-sm mt-1">{c.reason}</div>
            </div>
            <span className={`px-2 py-1 rounded text-xs font-bold whitespace-nowrap ${BADGE[c.verdict] || "bg-gray-700"}`}>{c.verdict} · {c.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
