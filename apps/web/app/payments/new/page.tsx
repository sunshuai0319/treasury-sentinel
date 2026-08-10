"use client";

import { useEffect, useState } from "react";

import { DecisionTimeline } from "@/components/decision-timeline/DecisionTimeline";
import {
  createPaymentRequest,
  paymentEventsUrl,
  startPaymentAnalysis,
  type DecisionStep,
  type PaymentRun
} from "@/lib/api/treasury";
import { usePaymentEvents } from "@/lib/api/usePaymentEvents";

const defaultPayload = {
  vendor_id: "vendor_demo",
  invoice_id: "inv_demo_001",
  amount_units: 420_000_000,
  recipient_address: "0x1111111111111111111111111111111111111111"
};

export default function NewPaymentPage() {
  const [run, setRun] = useState<PaymentRun | null>(null);
  const [requestId, setRequestId] = useState<string | undefined>(undefined);
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState<string | null>(null);
  const { events, error: eventError, connected } = usePaymentEvents(requestId);

  useEffect(() => {
    if (!requestId) return;
    const steps: DecisionStep[] = [];
    for (const event of events) {
      if (["primary", "critic", "final"].includes(event.event)) {
        const step = event.data as DecisionStep;
        const existing = steps.findIndex((item) => item.actor === step.actor);
        if (existing >= 0) {
          steps[existing] = step;
        } else {
          steps.push(step);
        }
      }
      if (event.event === "status") {
        const payload = event.data as { status: string; request_id: string };
        setStatus(`Status: ${payload.status}`);
      }
    }
    const finalStep = steps.find((step) => step.actor === "final");
    if (steps.length > 0) {
      setRun({
        request_id: requestId,
        scenario: "workflow",
        invoice_id: defaultPayload.invoice_id,
        vendor_id: defaultPayload.vendor_id,
        final_action: finalStep?.action || "REVIEW",
        timeline: steps
      });
    }
    if (!finalStep && connected) {
      setStatus("Analyzing with policy retrieval and agents...");
    }
  }, [connected, events, requestId]);

  useEffect(() => {
    if (eventError) {
      setError(eventError);
    }
  }, [eventError]);

  async function submitPayment() {
    setError(null);
    setStatus("Creating payment request");
    try {
      const request = await createPaymentRequest(defaultPayload, `web-demo-${Date.now()}`);
      setStatus("Analysis queued");
      setRequestId(request.request_id);
      await startPaymentAnalysis(request.request_id, `analysis-${request.request_id}`);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
      setStatus("Failed");
    }
  }

  return (
    <main className="shell">
      <section className="masthead">
        <div>
          <p className="eyebrow">Create payment</p>
          <h1>New request</h1>
          <p className="heroCopy">Submit a fixed approved-vendor payment into the real FastAPI workflow.</p>
        </div>
        <button className="primaryButton" onClick={submitPayment}>
          Submit demo payment
        </button>
      </section>

      <section className="console twoCols">
        <section className="copyPanel">
          <h2>Payload</h2>
          <pre>{JSON.stringify(defaultPayload, null, 2)}</pre>
          <p>{status.startsWith("Status:") ? status : `Status: ${status}`}</p>
          {error ? <p className="errorText">{error}</p> : null}
          {requestId ? <p>SSE: {paymentEventsUrl(requestId)}</p> : null}
        </section>
        <DecisionTimeline steps={run?.timeline || []} />
      </section>
    </main>
  );
}
