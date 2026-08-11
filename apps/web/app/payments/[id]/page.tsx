"use client";

import { useEffect, useState } from "react";
import { use } from "react";

import { DecisionTimeline } from "@/components/decision-timeline/DecisionTimeline";
import { getPaymentRequest, paymentEventsUrl, type PaymentRequest } from "@/lib/api/treasury";
import { buildDecisionSteps, usePaymentEvents } from "@/lib/api/usePaymentEvents";

export default function PaymentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [payment, setPayment] = useState<PaymentRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { events } = usePaymentEvents(payment?.request_id);
  const steps = buildDecisionSteps(events);

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
      {error ? <p className="errorText">{error}</p> : null}
      {payment ? (
        <section className="copyPanel">
          <p>
            Status: <strong className={`statusBadge status-${payment.status.toLowerCase()}`}>{payment.status}</strong>
          </p>
          {payment.final_action ? <p>Final action: {payment.final_action}</p> : null}
          <p>SSE: {paymentEventsUrl(payment.request_id)}</p>
        </section>
      ) : null}
      <DecisionTimeline steps={steps} />
      {payment ? (
        <section className="copyPanel">
          <pre>{JSON.stringify(payment, null, 2)}</pre>
        </section>
      ) : null}
    </main>
  );
}
