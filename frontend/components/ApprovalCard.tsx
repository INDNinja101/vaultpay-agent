"use client";
import { api } from "../lib/api";

export default function ApprovalCard({ approval, onDone }: { approval: any; onDone?: () => void }) {
  const item = approval.item || {};
  async function decide(decision: string) {
    await api(`/api/approvals/${approval.id}`, { method: "POST", body: JSON.stringify({ decision }) });
    onDone && onDone();
  }
  return (
    <div className="card space-y-2 border-yellow-700">
      <div className="flex justify-between"><span className="font-bold">{item.name}</span><span className="text-yellow-400 font-bold">${Number(item.price || 0).toFixed(2)}</span></div>
      <p className="text-sm text-gray-400">{item.category} · seller {item.seller} (rated {item.seller_rating})</p>
      <p className="text-sm">{approval.reason}</p>
      <p className="text-xs text-gray-500">In a live PayPal flow this approval opens the PayPal JS SDK checkout; the server then captures the order. In mock/sandbox demo mode the server capture runs immediately on Approve.</p>
      <div className="flex gap-3">
        <button className="btn" onClick={() => decide("APPROVE")}>Approve &amp; Pay with PayPal</button>
        <button className="btn btn-danger" onClick={() => decide("REJECT")}>Reject</button>
      </div>
    </div>
  );
}
