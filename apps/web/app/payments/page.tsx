import Link from "next/link";

const rows = [
  ["Normal payment", "vendor_demo", "420 USDC", "Auto-analysis then execution gate"],
  ["Duplicate invoice", "vendor_demo", "420 USDC", "Rejected by deterministic rules"],
  ["Over limit", "vendor_demo", "700 USDC", "Manual finance approval required"]
];

export default function PaymentsPage() {
  return (
    <main className="shell narrow">
      <p className="eyebrow">Payment queue</p>
      <h1>Payments</h1>
      <div className="tableCard">
        {rows.map(([title, vendor, amount, status]) => (
          <Link className="tableRow" href="/demo" key={title}>
            <strong>{title}</strong>
            <span>{vendor}</span>
            <span>{amount}</span>
            <small>{status}</small>
          </Link>
        ))}
      </div>
    </main>
  );
}
