"use client";

import { AlertTriangle, CheckCircle2, FileSearch, PauseCircle, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { DecisionTimeline } from "@/components/decision-timeline/DecisionTimeline";
import { runDemoScenario, type DecisionAction, type PaymentRun } from "@/lib/api/treasury";

const scenarios = [
  { id: "normal", label: "Normal", caption: "420 USDC approved vendor" },
  { id: "duplicate", label: "Duplicate", caption: "invoice hash already paid" },
  { id: "address_mismatch", label: "Wallet mismatch", caption: "recipient not whitelisted" },
  { id: "over_limit", label: "Over limit", caption: "finance review required" },
  { id: "pause", label: "Emergency pause", caption: "address anomaly threshold" }
];

const actionIcon: Record<DecisionAction, typeof CheckCircle2> = {
  APPROVE: CheckCircle2,
  REVIEW: FileSearch,
  REJECT: AlertTriangle,
  PAUSE: PauseCircle
};

export default function DemoPage() {
  const [active, setActive] = useState("normal");
  const [run, setRun] = useState<PaymentRun | null>(null);
  const [loading, setLoading] = useState(false);

  async function runScenario(id: string) {
    setActive(id);
    setLoading(true);
    setRun(await runDemoScenario(id));
    setLoading(false);
  }

  useEffect(() => {
    runScenario("normal");
  }, []);

  const finalAction = run?.final_action || "REVIEW";
  const FinalIcon = actionIcon[finalAction];

  return (
    <main className="shell">
      <section className="masthead">
        <div>
          <p className="eyebrow">KeeperHub Agents Onchain Demo</p>
          <h1>Treasury Sentinel</h1>
        </div>
        <div className={`verdict verdict-${finalAction.toLowerCase()}`}>
          <FinalIcon size={20} />
          <span>{loading ? "RUNNING" : finalAction}</span>
        </div>
      </section>

      <section className="console">
        <aside className="scenarioRail">
          <div className="railTitle">Demo scenarios</div>
          {scenarios.map((scenario) => (
            <button
              key={scenario.id}
              className={scenario.id === active ? "scenario active" : "scenario"}
              onClick={() => runScenario(scenario.id)}
            >
              <span>{scenario.label}</span>
              <small>{scenario.caption}</small>
            </button>
          ))}
        </aside>

        <DecisionTimeline steps={run?.timeline || []} />

        <aside className="evidence">
          <div className="panelHeader">
            <ShieldCheck size={18} />
            <span>Evidence</span>
          </div>
          <dl>
            <dt>Request</dt>
            <dd>{run?.request_id || "pending"}</dd>
            <dt>Invoice</dt>
            <dd>{run?.invoice_id || "pending"}</dd>
            <dt>Vendor</dt>
            <dd>{run?.vendor_id || "pending"}</dd>
            <dt>Policy refs</dt>
            <dd>{run?.timeline.at(-1)?.policy_refs.join(", ") || "pending"}</dd>
            <dt>KeeperHub</dt>
            <dd>{run?.keeperhub_execution_id || "blocked until live credentials"}</dd>
            <dt>Tx hash</dt>
            <dd>{run?.transaction_hash || "Base Sepolia after execution"}</dd>
          </dl>
        </aside>
      </section>
    </main>
  );
}
