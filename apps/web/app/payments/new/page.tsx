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

const paymentPresets = [
  {
    id: "normal",
    name: "Normal auto payment",
    expected: "APPROVE",
    description: "Approved vendor, matching wallet, 420 USDC. Should pass deterministic rules.",
    payload: {
      vendor_id: "vendor_demo",
      invoice_id: "inv_demo_001",
      amount_units: 420_000_000,
      recipient_address: "0x1111111111111111111111111111111111111111"
    }
  },
  {
    id: "over_limit",
    name: "Over 500 USDC",
    expected: "REVIEW",
    description: "700 USDC exceeds the auto-payment limit and should route to finance review.",
    payload: {
      vendor_id: "vendor_demo",
      invoice_id: "inv_demo_over_limit",
      amount_units: 700_000_000,
      recipient_address: "0x1111111111111111111111111111111111111111"
    }
  },
  {
    id: "wallet_mismatch",
    name: "Wallet mismatch",
    expected: "REJECT",
    description: "Recipient differs from the approved vendor wallet and should be rejected.",
    payload: {
      vendor_id: "vendor_demo",
      invoice_id: "inv_demo_mismatch",
      amount_units: 420_000_000,
      recipient_address: "0x2222222222222222222222222222222222222222"
    }
  }
] as const;

export default function NewPaymentPage() {
  const [selectedPresetId, setSelectedPresetId] = useState<(typeof paymentPresets)[number]["id"]>("normal");
  const [run, setRun] = useState<PaymentRun | null>(null);
  const [requestId, setRequestId] = useState<string | undefined>(undefined);
  const [status, setStatus] = useState("Ready");
  const [error, setError] = useState<string | null>(null);
  const { events, error: eventError, connected } = usePaymentEvents(requestId);
  const selectedPreset = paymentPresets.find((preset) => preset.id === selectedPresetId) || paymentPresets[0];
  const selectedPayload = selectedPreset.payload;
  // While analysis streams via SSE, switching presets would tear down the
  // request (requestId -> undefined) and lose the in-flight result.
  const analyzing = requestId !== undefined && connected;

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
        invoice_id: selectedPayload.invoice_id,
        vendor_id: selectedPayload.vendor_id,
        final_action: finalStep?.action || "REVIEW",
        timeline: steps
      });
    }
    if (!finalStep && connected) {
      setStatus("Analyzing with policy retrieval and agents...");
    }
  }, [connected, events, requestId, selectedPayload.invoice_id, selectedPayload.vendor_id]);

  useEffect(() => {
    if (eventError) {
      setError(eventError);
    }
  }, [eventError]);

  async function submitPayment() {
    setError(null);
    setRun(null);
    setRequestId(undefined);
    setStatus("Creating payment request");
    try {
      const request = await createPaymentRequest(selectedPayload, `web-demo-${selectedPreset.id}-${Date.now()}`);
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
          <p className="heroCopy">
            Submit preset payment requests into the real FastAPI workflow and compare approve, review and reject paths.
          </p>
        </div>
        <button className="primaryButton" onClick={submitPayment}>
          Submit {selectedPreset.name}
        </button>
      </section>

      <section className="console twoCols">
        <section className="copyPanel">
          <h2>Payload</h2>
          <div className="presetList" aria-label="Payment presets">
            {paymentPresets.map((preset) => (
              <button
                className={`presetButton ${preset.id === selectedPresetId ? "active" : ""}`}
                key={preset.id}
                disabled={analyzing}
                onClick={() => {
                  setSelectedPresetId(preset.id);
                  setRun(null);
                  setRequestId(undefined);
                  setStatus("Ready");
                  setError(null);
                }}
                type="button"
              >
                <span>{preset.name}</span>
                <small>{preset.expected}</small>
              </button>
            ))}
          </div>
          <p className="presetDescription">{selectedPreset.description}</p>
          <pre>{JSON.stringify(selectedPayload, null, 2)}</pre>
          <p>{status.startsWith("Status:") ? status : `Status: ${status}`}</p>
          {error ? <p className="errorText">{error}</p> : null}
          {requestId ? (
            <p className="sseEndpoint">
              SSE: <code>{paymentEventsUrl(requestId)}</code>
            </p>
          ) : null}
        </section>
        <DecisionTimeline steps={run?.timeline || []} />
      </section>
    </main>
  );
}
