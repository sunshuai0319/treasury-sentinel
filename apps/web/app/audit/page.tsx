"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import Pagination from "@/components/Pagination";
import { baseScanTxUrl, formatPaymentTime, listPaymentRequests, type PaymentRequest } from "@/lib/api/treasury";

const pageSize = 5;

export default function AuditIndexPage() {
  const [requests, setRequests] = useState<PaymentRequest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(requests.length / pageSize));
  const safePage = Math.min(page, pageCount);
  const visible = requests.slice((safePage - 1) * pageSize, safePage * pageSize);

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
      <p className="eyebrow">Audit trail</p>
      <h1>Audit trail</h1>
      <p className="heroCopy">
        Every payment request and a one-click path to its full Primary/Critic/Final decision trail.
      </p>

      {error ? <p className="errorText">{error}</p> : null}

      {requests.length === 0 ? (
        <p className="emptyState">No payment requests yet — create one in New Payment to see its audit trail.</p>
      ) : (
        <section className="tableCard" aria-label="Audit trails">
          <div className="tableRow paymentsHeader" aria-hidden="true">
            <span>Request</span>
            <span>Vendor</span>
            <span>Invoice</span>
            <span>Amount</span>
            <span>Created</span>
            <span>Status</span>
            <span>On-chain</span>
          </div>
          {visible.map((payment) => {
            const txUrl = baseScanTxUrl(payment.transaction_hash);
            return (
              // 整行拆为 div:HTML 不允许 <a> 嵌套 <a>,详情入口与 BaseScan 外链必须独立
              <div className="tableRow paymentsRow" key={payment.request_id}>
                <Link href={`/audit/${payment.request_id}`}>
                  <strong>{payment.request_id}</strong>
                </Link>
                <span>{payment.vendor_id}</span>
                <span>{payment.invoice_id}</span>
                <span>{`${(payment.amount_units / 1_000_000).toLocaleString()} USDC`}</span>
                <span>{formatPaymentTime(payment.created_at)}</span>
                <span className={`statusBadge status-${payment.status.toLowerCase()}`}>{payment.status}</span>
                {txUrl ? (
                  <a className="txLink" href={txUrl} target="_blank" rel="noreferrer">
                    BaseScan ↗
                  </a>
                ) : (
                  <span aria-label="No transaction yet">—</span>
                )}
              </div>
            );
          })}
        </section>
      )}
      <Pagination page={safePage} pageCount={pageCount} onPageChange={setPage} />
    </main>
  );
}
