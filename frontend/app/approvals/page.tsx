"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import ApprovalCard from "../../components/ApprovalCard";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const load = useCallback(() => { api("/api/approvals").then((d) => setApprovals(d.approvals)).catch(() => {}); }, []);
  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, [load]);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Approval inbox</h1>
      <p className="text-gray-400 text-sm">The agent paused these because a rule said ASK. Nothing is paid until you approve.</p>
      {!approvals.length && <p className="text-gray-400">No pending approvals. Run the &quot;Premium Gift Hamper&quot; task to create one.</p>}
      {approvals.map((a) => <ApprovalCard key={a.id} approval={a} onDone={load} />)}
    </div>
  );
}
