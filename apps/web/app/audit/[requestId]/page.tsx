"use client";

import { redirect } from "next/navigation";
import { useEffect, useState, use } from "react";

import { DecisionTimeline } from "@/components/decision-timeline/DecisionTimeline";
import { baseScanTxUrl, getPaymentRequest, paymentEventsUrl, type PaymentRequest } from "@/lib/api/treasury";
import { buildDecisionSteps, usePaymentEvents } from "@/lib/api/usePaymentEvents";

export default function AuditPage({ params }: { params: Promise<{ requestId: string }> }) {
  const { requestId } = use(params);
  // The former "guide" page is gone; point old links at the audit index.
  if (requestId === "demo-normal") redirect("/audit");
  const { events, eventsRequestId, error } = usePaymentEvents(requestId);
  const steps = buildDecisionSteps(eventsRequestId === requestId ? events : []);
  const [payment, setPayment] = useState<PaymentRequest | null>(null);
  const txUrl = payment ? baseScanTxUrl(payment.transaction_hash) : null;

  useEffect(() => {
    let cancelled = false;
    getPaymentRequest(requestId)
      .then((result) => {
        if (!cancelled) setPayment(result);
      })
      .catch(() => {
        // SSE already streams the decision trail; a failed detail fetch should not
        // hide the timeline, it only loses the on-chain link.
      });
    return () => {
      cancelled = true;
    };
  }, [requestId]);

  return (
    <main className="shell narrow">
      <p className="eyebrow">Audit trail</p>
      <h1>{requestId}</h1>
      <section className="copyPanel">
        <p>API endpoint: <code>{paymentEventsUrl(requestId)}</code></p>
        {txUrl ? (
          <p>
            On-chain:{" "}
            <a className="txLink" href={txUrl} target="_blank" rel="noreferrer">
              View on BaseScan ↗
            </a>
          </p>
        ) : null}
        {error ? <p className="errorText">{error}</p> : null}
      </section>
      <DecisionTimeline steps={steps} />
    </main>
  );
}
