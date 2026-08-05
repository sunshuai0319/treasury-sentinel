export default async function AuditPage({ params }: { params: Promise<{ requestId: string }> }) {
  const { requestId } = await params;
  return (
    <main className="shell narrow">
      <p className="eyebrow">Audit trail</p>
      <h1>{requestId}</h1>
      <section className="copyPanel">
        <p>Open the API SSE endpoint to inspect ordered Primary, Critic, Final and status events:</p>
        <code>/api/payment-requests/{requestId}/events</code>
      </section>
    </main>
  );
}
