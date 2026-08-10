import Link from "next/link";

export default function Home() {
  return (
    <main className="shell narrow">
      <section className="masthead">
        <div>
          <p className="eyebrow">Policy-aware autonomous treasury</p>
          <h1>Treasury Sentinel</h1>
          <p className="heroCopy">
            Primary/Critic Agent decisions are constrained by deterministic rules, PostgreSQL facts, policy retrieval and
            a guarded Base Sepolia contract.
          </p>
        </div>
      </section>
      <section className="navGrid">
        <Link href="/demo">Run five demo scenarios</Link>
        <Link href="/payments">Inspect payments</Link>
        <Link href="/approvals">Review escalations</Link>
        <Link href="/audit">Audit trail</Link>
      </section>
    </main>
  );
}
