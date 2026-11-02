export default function PolicyPreview({ policy }: { policy: any }) {
  if (!policy) return null;
  const rows: [string, string][] = [
    ["Total budget", `$${policy.total_budget_usd}`],
    ["Ask me above", `$${policy.per_item_ask_above_usd} per item`],
    ["Hard cap", `$${policy.per_item_hard_cap_usd} per item`],
    ["Blocked categories", (policy.blocked_categories || []).join(", ") || "none"],
    ["Allowed categories", (policy.allowed_categories || []).join(", ") || "all (except blocked)"],
    ["Min seller rating", String(policy.min_seller_rating)],
    ["Auto-allow inside rules", policy.auto_allow ? "yes" : "no"],
  ];
  return (
    <div className="card">
      <h3 className="font-bold mb-2">Policy preview — this is what the engine will enforce</h3>
      <table className="w-full text-sm">
        <tbody>{rows.map(([k, v]) => (
          <tr key={k} className="border-b border-gray-800"><td className="py-1 text-gray-400">{k}</td><td className="py-1 text-right">{v}</td></tr>
        ))}</tbody>
      </table>
      <pre className="mt-3 text-xs bg-black/40 p-3 rounded overflow-auto">{JSON.stringify(policy, null, 2)}</pre>
    </div>
  );
}
