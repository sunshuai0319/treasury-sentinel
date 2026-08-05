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
};

export const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

export async function runDemoScenario(id: string): Promise<PaymentRun> {
  const response = await fetch(`${apiBase}/demo/run/${id}`, { method: "POST", cache: "no-store" });
  if (!response.ok) throw new Error(`Demo scenario failed: ${response.status}`);
  return (await response.json()) as PaymentRun;
}

export function paymentEventsUrl(requestId: string): string {
  return `${apiBase}/payment-requests/${requestId}/events`;
}
