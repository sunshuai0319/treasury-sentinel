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
      <p className="heroCopy">
        Use the new-payment flow to create a real FastAPI request, run analysis and inspect the SSE audit stream.
      </p>
      <p>
        <Link className="primaryLink" href="/payments/new">
          Create demo payment
        </Link>
      </p>
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
