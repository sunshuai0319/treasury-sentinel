import Link from "next/link";

import { paymentEventsUrl } from "@/lib/api/treasury";

export default async function AuditPage({ params }: { params: Promise<{ requestId: string }> }) {
  const { requestId } = await params;
  const isDemoGuide = requestId === "demo-normal";
  const eventsUrl = paymentEventsUrl(requestId);

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
          </>
        ) : (
          <>
            <p>这个页面对应后端 SSE 审计事件流，按顺序输出 Primary、Critic、Final 和 status events。</p>
            <p>
              API endpoint: <code>{eventsUrl}</code>
            </p>
          </>
        )}
      </section>
    </main>
  );
}
