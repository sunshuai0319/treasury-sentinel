import { getPaymentRequest, paymentEventsUrl } from "@/lib/api/treasury";

export default async function PaymentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let payment;
  let error: string | null = null;
  try {
    payment = await getPaymentRequest(id);
  } catch (exc) {
    error = exc instanceof Error ? exc.message : String(exc);
  }

  return (
    <main className="shell narrow">
      <p className="eyebrow">Payment detail</p>
      <h1>{id}</h1>
      <section className="copyPanel">
        {error ? (
          <p className="errorText">{error}</p>
        ) : (
          <>
            <pre>{JSON.stringify(payment, null, 2)}</pre>
            <p>SSE: {payment ? paymentEventsUrl(payment.request_id) : "pending"}</p>
          </>
        )}
      </section>
    </main>
  );
}
