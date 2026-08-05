export default function ApprovalsPage() {
  return (
    <main className="shell narrow">
      <p className="eyebrow">Human escalation</p>
      <h1>Approvals</h1>
      <section className="copyPanel">
        <p>
          Requests land here when policy retrieval, Primary/Critic output, wallet checks, or deterministic rules cannot
          prove auto-payment safety.
        </p>
        <p>KeeperHub execution remains fail-closed until live credentials and wallet roles are configured.</p>
      </section>
    </main>
  );
}
