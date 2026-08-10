"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, XCircle } from "lucide-react";

import {
  decidePaymentRequest,
  listPaymentRequests,
  type PaymentRequest
} from "@/lib/api/treasury";

export default function ApprovalsPage() {
  const [requests, setRequests] = useState<PaymentRequest[]>([]);
  const [approver, setApprover] = useState("finance.lead");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setRequests(await listPaymentRequests("REVIEW"));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleDecision(requestId: string, decision: "approve" | "reject") {
    setBusyId(requestId);
    setError(null);
    try {
      await decidePaymentRequest(requestId, decision, approver);
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="shell narrow">
      <p className="eyebrow">Human escalation</p>
      <h1>Approvals</h1>
      <section className="copyPanel">
        <p>
          Requests land here when policy retrieval, Primary/Critic output, wallet checks, or deterministic rules cannot
          prove auto-payment safety. Approve to move a request toward execution, or reject to decline it.
        </p>
        <label className="approvalsApprover">
          Approver
          <input value={approver} onChange={(event) => setApprover(event.target.value)} />
        </label>
      </section>

      {error ? <p className="errorText">{error}</p> : null}

      {requests.length === 0 ? (
        <p className="emptyState">No payments awaiting review.</p>
      ) : (
        <section className="tableCard" aria-label="Review escalations">
          <div className="tableRow approvalHeader" aria-hidden="true">
            <span>Request</span>
            <span>Vendor</span>
            <span>Invoice</span>
            <span>Amount</span>
            <span>Actions</span>
          </div>
          {requests.map((payment) => (
            <div className="tableRow approvalRow" key={payment.request_id}>
              <Link href={`/audit/${payment.request_id}`} title="View audit trail">
                {payment.request_id}
              </Link>
              <span>{payment.vendor_id}</span>
              <span>{payment.invoice_id}</span>
              <span>{`${(payment.amount_units / 1_000_000).toLocaleString()} USDC`}</span>
              <span className="rowActions">
                <button
                  className="approveButton"
                  disabled={busyId !== null}
                  onClick={() => handleDecision(payment.request_id, "approve")}
                  type="button"
                >
                  <CheckCircle2 size={14} />
                  Approve
                </button>
                <button
                  className="rejectButton"
                  disabled={busyId !== null}
                  onClick={() => handleDecision(payment.request_id, "reject")}
                  type="button"
                >
                  <XCircle size={14} />
                  Reject
                </button>
              </span>
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
