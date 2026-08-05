import { AlertTriangle, CheckCircle2, FileSearch, PauseCircle } from "lucide-react";

import type { DecisionAction, DecisionStep } from "@/lib/api/treasury";

const actionIcon: Record<DecisionAction, typeof CheckCircle2> = {
  APPROVE: CheckCircle2,
  REVIEW: FileSearch,
  REJECT: AlertTriangle,
  PAUSE: PauseCircle
};

export function DecisionTimeline({ steps }: { steps: DecisionStep[] }) {
  return (
    <section className="timeline">
      <div className="panelHeader">
        <FileSearch size={18} />
        <span>Decision chain</span>
      </div>
      {steps.map((step) => {
        const Icon = actionIcon[step.action];
        return (
          <article className="step" key={step.actor}>
            <div className="stepMark">
              <Icon size={18} />
            </div>
            <div>
              <div className="stepTop">
                <strong>{step.actor}</strong>
                <span>{step.action}</span>
              </div>
              <p>{step.reasons.join("; ")}</p>
            </div>
          </article>
        );
      })}
    </section>
  );
}
