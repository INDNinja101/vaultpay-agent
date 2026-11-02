import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">AI agents can shop. VaultPay is the agent you can actually trust with money.</h1>
      <p className="text-gray-300">It spends only inside rules <em>you</em> wrote, asks when it&apos;s unsure, refuses when a rule breaks, and shows you exactly why — every time. The LLM parses and explains; deterministic code decides ALLOW / ASK / DENY.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card"><h2 className="font-bold text-green-400">ALLOW</h2><p>Buys fest supplies inside budget — pays via PayPal on its own.</p></div>
        <div className="card"><h2 className="font-bold text-yellow-400">ASK</h2><p>A $31 item over the $25 threshold pauses for your approval.</p></div>
        <div className="card"><h2 className="font-bold text-red-400">DENY</h2><p>A blocked subscription is refused — no PayPal order is ever created.</p></div>
      </div>
      <div className="flex gap-4">
        <Link className="btn" href="/rules">1. Set your rules</Link>
        <Link className="btn" href="/tasks">2. Give the agent a task</Link>
      </div>
    </div>
  );
}
