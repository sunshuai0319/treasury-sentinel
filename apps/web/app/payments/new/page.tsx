"use client";

import { useState } from "react";

import { DecisionTimeline } from "@/components/decision-timeline/DecisionTimeline";
import {
  createPaymentRequest,
  paymentEventsUrl,
  startPaymentAnalysis,
  type DecisionStep,
  type PaymentRun
} from "@/lib/api/treasury";

const defaultPayload = {
  vendor_id: "vendor_demo",
  invoice_id: "inv_demo_001",
  amount_units: 420_000_000,
  recipient_address: "0x1111111111111111111111111111111111111111"
};

export default function NewPaymentPage() {
  const [run, setRun] = useState<PaymentRun | null>(null);
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState<string | null>(null);

  async function submitPayment() {
    setError(null);
    setStatus("Creating payment request");
    try {
      const request = await createPaymentRequest(defaultPayload, `web-demo-${Date.now()}`);
      setStatus("Analysis queued");
      await startPaymentAnalysis(request.request_id);
      subscribeToAnalysis(request.request_id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
      setStatus("Failed");
    }
  }

  function subscribeToAnalysis(requestId: string) {
    const source = new EventSource(paymentEventsUrl(requestId));
    const steps: DecisionStep[] = [];
    source.addEventListener("heartbeat", () => {
      setStatus("Analyzing with policy retrieval and agents...");
    });
    for (const eventName of ["primary", "critic", "final"]) {
      source.addEventListener(eventName, (event) => {
        const step = JSON.parse(event.data) as DecisionStep;
        const existing = steps.findIndex((item) => item.actor === step.actor);
        if (existing >= 0) {
          steps[existing] = step;
        } else {
          steps.push(step);
        }
        setRun({
          request_id: requestId,
          scenario: "workflow",
          invoice_id: defaultPayload.invoice_id,
          vendor_id: defaultPayload.vendor_id,
          final_action: step.actor === "final" ? step.action : "REVIEW",
          timeline: [...steps]
        });
        setStatus(step.actor === "final" ? `Final action: ${step.action}` : `${step.actor} completed`);
      });
    }
    source.addEventListener("status", (event) => {
      const payload = JSON.parse(event.data) as { status: string; request_id: string };
      setStatus(`Status: ${payload.status}`);
      if (!["SUBMITTED", "ANALYZING"].includes(payload.status)) {
        source.close();
      }
    });
    source.onerror = () => {
      source.close();
    };
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
          <p>Status: {status}</p>
          {error ? <p className="errorText">{error}</p> : null}
          {run ? <p>SSE: {paymentEventsUrl(run.request_id)}</p> : null}
        </section>
        <DecisionTimeline steps={run?.timeline || []} />
      </section>
    </main>
  );
}
