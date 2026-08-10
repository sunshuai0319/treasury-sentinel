"use client";

import { redirect } from "next/navigation";
import { use } from "react";

import { DecisionTimeline } from "@/components/decision-timeline/DecisionTimeline";
import { paymentEventsUrl } from "@/lib/api/treasury";
import { buildDecisionSteps, usePaymentEvents } from "@/lib/api/usePaymentEvents";

export default function AuditPage({ params }: { params: Promise<{ requestId: string }> }) {
  const { requestId } = use(params);
  // The former "guide" page is gone; point old links at the audit index.
  if (requestId === "demo-normal") redirect("/audit");
  const { events, eventsRequestId, error } = usePaymentEvents(requestId);
  const steps = buildDecisionSteps(eventsRequestId === requestId ? events : []);

  return (
    <main className="shell narrow">
      <p className="eyebrow">Audit trail</p>
      <h1>{requestId}</h1>
      <section className="copyPanel">
        <p>API endpoint: <code>{paymentEventsUrl(requestId)}</code></p>
        {error ? <p className="errorText">{error}</p> : null}
      </section>
      <DecisionTimeline steps={steps} />
    </main>
  );
}
