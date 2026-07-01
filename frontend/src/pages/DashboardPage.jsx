// Dashboard (stub for slice 1). The real data-sharing overview — stat row,
// portable-address card, recent activity, and a "data you've shared" breakdown —
// lands in slice 2. For now this is a welcoming hub that points a first-time
// visitor straight at the first thing worth trying.
const LINKS = [
  ["accounts", "Bank Accounts", "Your net worth and accounts, shown only with your consent."],
  ["control", "Control Centre", "Connections, permissions, and every access — verifiable in your browser."],
  ["assistant", "Assistant", "A scoped, revocable agent that suggests, never acts."],
  ["address", "Portable Address", "A handle that routes payments without exposing your account."],
  ["credentials", "Credentials", "Prove a fact without sharing the data behind it."],
  ["compare", "Old vs New", "Why token-based access beats credential screen-scraping."],
];

export default function DashboardPage({ onNavigate }) {
  return (
    <>
      <div className="card stub-hero">
        <h2>You&apos;re in control</h2>
        <p className="section-note">
          A data-sharing overview lands here next: active connections and consents, recent access,
          and what you&apos;ve shared, at a glance. In the meantime, jump straight in.
        </p>
        <p className="stub-tip">
          Tip: revoke a bank in <strong>Control Centre</strong> and watch it disappear from{" "}
          <strong>Bank Accounts</strong>.
        </p>
      </div>

      <div className="stub-grid">
        {LINKS.map(([key, title, blurb]) => (
          <button key={key} type="button" className="card stub-link" onClick={() => onNavigate(key)}>
            <strong>{title}</strong>
            <span className="section-note">{blurb}</span>
            <span className="stub-arrow" aria-hidden="true">
              →
            </span>
          </button>
        ))}
      </div>
    </>
  );
}
