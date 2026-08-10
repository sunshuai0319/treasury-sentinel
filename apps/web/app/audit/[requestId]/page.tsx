"use client";

import Link from "next/link";
import { use } from "react";

import { DecisionTimeline } from "@/components/decision-timeline/DecisionTimeline";
import { paymentEventsUrl, type DecisionStep } from "@/lib/api/treasury";
import { buildDecisionSteps, usePaymentEvents } from "@/lib/api/usePaymentEvents";

const exampleSteps: DecisionStep[] = [
  {
    actor: "primary",
    action: "APPROVE",
    confidence: 0.72,
    reasons: [
      "primary proposes payment only after retrieval and deterministic rule check (检索政策并经过确定性规则检查后，主代理才建议付款)"
    ],
    policy_refs: ["payment-policy#2.1"]
  },
  {
    actor: "critic",
    action: "REVIEW",
    confidence: 0.78,
    reasons: [
      "critic requires deterministic rules to make the final execution decision (批评代理要求以确定性规则作出最终执行决定)"
    ],
    policy_refs: ["payment-policy#2.1"]
  },
  {
    actor: "final",
    action: "APPROVE",
    confidence: 1,
    reasons: [
      "approved vendor, matching wallet, unpaid invoice, amount <= 500 USDC (供应商已批准、钱包匹配、发票未支付、金额≤500 USDC)"
    ],
    policy_refs: ["payment-policy#2.1"]
  }
];

export default function AuditPage({ params }: { params: Promise<{ requestId: string }> }) {
  const { requestId } = use(params);
  const isDemoGuide = requestId === "demo-normal";
  const { events, eventsRequestId, error } = usePaymentEvents(isDemoGuide ? undefined : requestId);
  const steps = buildDecisionSteps(eventsRequestId === requestId ? events : []);

  return (
    <main className="shell narrow">
      <p className="eyebrow">Audit trail</p>
      <h1>{requestId}</h1>
      <section className="copyPanel">
        {isDemoGuide ? (
          <>
            <p>
              <strong>demo-normal</strong> 是前端固定演示场景的名字，不是后端 PostgreSQL 里的真实付款请求
              ID，所以它不会直接返回一条真实审计流。
            </p>
            <p>
              要查看真实审计轨迹，请先进入 <Link href="/payments/new">New Payment</Link> 创建请求，拿到
              <strong> pay_xxx</strong> 格式的 request ID 后打开 <code>/audit/pay_xxx</code>。
            </p>
            <p>
              下面是 <strong>Normal auto payment</strong> 场景的示例决策链，展示真实审计页的形态（静态示例，
              不会实时更新）。
            </p>
          </>
        ) : (
          <>
            <p>API endpoint: <code>{paymentEventsUrl(requestId)}</code></p>
            {error ? <p className="errorText">{error}</p> : null}
          </>
        )}
      </section>
      <DecisionTimeline steps={isDemoGuide ? exampleSteps : steps} />
    </main>
  );
}
