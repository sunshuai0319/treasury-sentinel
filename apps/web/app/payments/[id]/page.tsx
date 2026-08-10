"use client";

import { useEffect, useState } from "react";
import { use } from "react";

import { getPaymentRequest, paymentEventsUrl, type PaymentRequest } from "@/lib/api/treasury";

export default function PaymentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [payment, setPayment] = useState<PaymentRequest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getPaymentRequest(id)
      .then((result) => {
        if (!cancelled) setPayment(result);
      })
      .catch((exc) => {
        if (!cancelled) setError(exc instanceof Error ? exc.message : String(exc));
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <main className="shell narrow">
      <p className="eyebrow">Payment detail</p>
      <h1>{id}</h1>
      <section className="copyPanel">
        {error ? (
          <p className="errorText">{error}</p>
        ) : payment ? (
          <>
            <p>
              Status: <strong className={`statusBadge status-${payment.status.toLowerCase()}`}>{payment.status}</strong>
            </p>
            <pre>{JSON.stringify(payment, null, 2)}</pre>
            <p>SSE: {paymentEventsUrl(payment.request_id)}</p>
          </>
        ) : (
          <p className="emptyState">Loading…</p>
        )}
      </section>
    </main>
  );
}
