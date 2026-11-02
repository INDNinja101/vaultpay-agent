import "./globals.css";
import Link from "next/link";

export const metadata = { title: "VaultPay Agent", description: "The AI shopping agent you can trust with money" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="flex gap-6 items-center px-6 py-4 border-b border-gray-800">
          <Link href="/" className="font-bold text-xl text-white">VaultPay Agent</Link>
          <Link href="/rules" className="text-blue-400 hover:underline">Rules</Link>
          <Link href="/tasks" className="text-blue-400 hover:underline">Tasks</Link>
          <Link href="/approvals" className="text-blue-400 hover:underline">Approvals</Link>
          <Link href="/audit" className="text-blue-400 hover:underline">Audit</Link>
        </nav>
        <main className="max-w-4xl mx-auto p-6">{children}</main>
      </body>
    </html>
  );
}
