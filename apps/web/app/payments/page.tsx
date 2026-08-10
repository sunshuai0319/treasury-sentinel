"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { listPaymentRequests, type PaymentRequest } from "@/lib/api/treasury";

export default function PaymentsPage() {
  const [requests, setRequests] = useState<PaymentRequest[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setRequests(await listPaymentRequests());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <main className="shell narrow">
      <p className="eyebrow">Payment queue</p>
      <h1>Payments</h1>
      <p className="heroCopy">
        Every real FastAPI payment request, its current status and a link to the SSE audit stream.
      </p>
      <p>
        <Link className="primaryLink" href="/payments/new">
          Create demo payment
        </Link>
      </p>

      {error ? <p className="errorText">{error}</p> : null}

      {requests.length === 0 ? (
        <p className="emptyState">No payment requests yet — create one above to see it here.</p>
      ) : (
        <section className="tableCard" aria-label="Payment requests">
          <div className="tableRow paymentsHeader" aria-hidden="true">
            <span>Request</span>
            <span>Vendor</span>
            <span>Invoice</span>
            <span>Amount</span>
            <span>Status</span>
          </div>
          {requests.map((payment) => (
            <Link className="tableRow paymentsRow" href={`/payments/${payment.request_id}`} key={payment.request_id}>
              <strong>{payment.request_id}</strong>
              <span>{payment.vendor_id}</span>
              <span>{payment.invoice_id}</span>
              <span>{`${(payment.amount_units / 1_000_000).toLocaleString()} USDC`}</span>
              <span className={`statusBadge status-${payment.status.toLowerCase()}`}>{payment.status}</span>
            </Link>
          ))}
        </section>
      )}
    </main>
  );
}
