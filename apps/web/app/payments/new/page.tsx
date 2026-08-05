"use client";

import { useState } from "react";

import { DecisionTimeline } from "@/components/decision-timeline/DecisionTimeline";
import {
  analyzePaymentRequest,
  createPaymentRequest,
  paymentEventsUrl,
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
      setStatus("Running Primary/Critic/Rules analysis");
      const analyzed = await analyzePaymentRequest(request.request_id);
      setRun(analyzed);
      setStatus(`Final action: ${analyzed.final_action}`);
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
          <p>Status: {status}</p>
          {error ? <p className="errorText">{error}</p> : null}
          {run ? <p>SSE: {paymentEventsUrl(run.request_id)}</p> : null}
        </section>
        <DecisionTimeline steps={run?.timeline || []} />
      </section>
    </main>
  );
}
