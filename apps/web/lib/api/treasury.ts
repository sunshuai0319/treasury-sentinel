export type DecisionAction = "APPROVE" | "REVIEW" | "REJECT" | "PAUSE";

export type DecisionStep = {
  actor: "primary" | "critic" | "final";
  action: DecisionAction;
  confidence: number;
  reasons: string[];
  policy_refs: string[];
};

export type PaymentRun = {
  request_id: string;
  scenario: string;
  invoice_id: string;
  vendor_id: string;
  final_action: DecisionAction;
  timeline: DecisionStep[];
  keeperhub_execution_id?: string | null;
  transaction_hash?: string | null;
};

export type PaymentRequest = {
  request_id: string;
  vendor_id: string;
  invoice_id: string;
  amount_units: number;
  recipient_address: string;
  status: string;
  final_action?: DecisionAction | null;
  decision_hash?: string | null;
  keeperhub_execution_id?: string | null;
  transaction_hash?: string | null;
  created_at: string;
};

// Backend stores created_at as naive UTC; keep it in UTC for display so the
// timestampless ISO string is not shifted by the browser timezone.
export function formatPaymentTime(iso: string): string {
  return iso.replace("T", " ").slice(0, 16);
}

// BaseScan block explorer, defaulting to Base Sepolia where the treasury
// guard contract is currently deployed (chain_id 84532). Override for mainnet:
//   NEXT_PUBLIC_BASE_SCAN_BASE_URL=https://basescan.org
const baseScanBaseUrl = process.env.NEXT_PUBLIC_BASE_SCAN_BASE_URL || "https://sepolia.basescan.org";

export function baseScanTxUrl(txHash: string | null | undefined): string | null {
  if (!txHash) return null;
  return `${baseScanBaseUrl}/tx/${txHash}`;
}

export type CreatePaymentPayload = {
  vendor_id: string;
  invoice_id: string;
  amount_units: number;
  recipient_address: string;
};

export const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

export async function runDemoScenario(id: string): Promise<PaymentRun> {
  const response = await fetch(`${apiBase}/demo/run/${id}`, { method: "POST", cache: "no-store" });
  if (!response.ok) throw new Error(`Demo scenario failed: ${response.status}`);
  return (await response.json()) as PaymentRun;
}

export async function createPaymentRequest(
  payload: CreatePaymentPayload,
  idempotencyKey: string
): Promise<PaymentRequest> {
  const response = await fetch(`${apiBase}/payment-requests`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`Create payment failed: ${response.status}`);
  return (await response.json()) as PaymentRequest;
}

export async function analyzePaymentRequest(requestId: string, idempotencyKey?: string): Promise<PaymentRun> {
  const response = await fetch(`${apiBase}/payment-requests/${requestId}/analyze`, {
    method: "POST",
    cache: "no-store",
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined
  });
  if (!response.ok) throw new Error(`Analyze payment failed: ${response.status}`);
  return (await response.json()) as PaymentRun;
}

export async function startPaymentAnalysis(requestId: string, idempotencyKey?: string): Promise<PaymentRequest> {
  const response = await fetch(`${apiBase}/payment-requests/${requestId}/analyze`, {
    method: "POST",
    cache: "no-store",
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined
  });
  if (!response.ok) throw new Error(`Start analysis failed: ${response.status}`);
  return (await response.json()) as PaymentRequest;
}

export async function getPaymentRequest(requestId: string): Promise<PaymentRequest> {
  const response = await fetch(`${apiBase}/payment-requests/${requestId}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Get payment failed: ${response.status}`);
  return (await response.json()) as PaymentRequest;
}

export async function listPaymentRequests(status?: string): Promise<PaymentRequest[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const response = await fetch(`${apiBase}/payment-requests${query}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`List payments failed: ${response.status}`);
  return (await response.json()) as PaymentRequest[];
}

export async function decidePaymentRequest(
  requestId: string,
  decision: "approve" | "reject",
  approver: string,
  reason?: string
): Promise<PaymentRequest> {
  const response = await fetch(`${apiBase}/payment-requests/${requestId}/${decision}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approver, reason: reason || "" })
  });
  if (!response.ok) throw new Error(`Payment ${decision} failed: ${response.status}`);
  return (await response.json()) as PaymentRequest;
}

export function paymentEventsUrl(requestId: string, lastEventId?: string): string {
  const url = new URL(`${apiBase}/payment-requests/${requestId}/events`);
  if (lastEventId) url.searchParams.set("last_event_id", lastEventId);
  return url.toString();
}
