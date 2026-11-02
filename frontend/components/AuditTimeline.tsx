const COLORS: Record<string, string> = {
  ALLOW: "text-green-400 border-green-800", PAID: "text-green-300 border-green-800",
  ASK: "text-yellow-400 border-yellow-800", DENY: "text-red-400 border-red-800",
  REJECTED: "text-red-300 border-red-900", FAILED: "text-red-500 border-red-900",
  INFO: "text-gray-300 border-gray-700", WEBHOOK: "text-blue-300 border-blue-900",
};

export default function AuditTimeline({ events }: { events: any[] }) {
  if (!events?.length) return <p className="text-gray-400">No audit events yet.</p>;
  return (
    <div className="space-y-2">
      {events.map((e) => (
        <div key={e.id} className={`card border-l-4 ${COLORS[e.type] || COLORS.INFO}`}>
          <div className="flex justify-between text-xs text-gray-500">
            <span className={`font-bold ${COLORS[e.type]?.split(" ")[0] || ""}`}>{e.type}</span>
            <span>{e.created_at ? new Date(e.created_at).toLocaleString() : ""}{e.task_id ? ` · task #${e.task_id}` : ""}</span>
          </div>
          <p className="text-sm mt-1">{e.message}</p>
        </div>
      ))}
    </div>
  );
}
