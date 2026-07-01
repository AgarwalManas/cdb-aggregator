import Icon from "../components/Icon.jsx";

// Old vs New (Trust & Privacy): screen-scraping vs consent-based access, side by
// side, plus the principles behind the new model (which absorbs the former
// "Consent principles" page). Static explainer content — honesty-adjusted.
const OLD = [
  ["key", "Share usernames and passwords", "You hand an app your bank login, and it signs in as you."],
  ["users", "Broad, unclear access", "Whoever has the login can see everything — far more than needed."],
  ["unlock", "Hard to revoke", "The only real off-switch is changing your password and hoping apps forget."],
  ["eyeOff", "Opaque and untraceable", "No record of who read what, or when."],
  ["alert", "Brittle and higher risk", "Credentials can be stored or reused, and a page redesign breaks the scraper."],
];

const NEW = [
  ["fileCheck", "Grant consent, not credentials", "Authorize a scoped token; your password never leaves your bank."],
  ["sliders", "Granular permissions", "Choose exactly what's shared, for which accounts, and for how long."],
  ["refresh", "Easy to revoke", "Revoke anytime — access ends immediately, and grants expire on their own."],
  ["eye", "Transparent and traceable", "Every access is logged, attributed, and verifiable in your browser."],
  ["shield", "Lower risk by design", "No stored credentials; reads are minimized to what you granted."],
];

const PRINCIPLES = [
  ["check", "Explicit consent"],
  ["target", "Purpose-scoped"],
  ["clock", "Time-bound access"],
  ["database", "Data minimization"],
  ["eye", "Transparency & traceability"],
  ["lock", "Security by design"],
];

function Side({ variant, title, subtitle, items }) {
  return (
    <div className={`vs-side vs-${variant}`}>
      <div className="vs-head">
        <h3>{title}</h3>
        <span className="section-note">{subtitle}</span>
      </div>
      <ul>
        {items.map(([icon, name, body]) => (
          <li key={name}>
            <span className="vs-icon">
              <Icon name={icon} />
            </span>
            <span>
              <strong>{name}</strong>
              <span className="section-note">{body}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ComparePage() {
  return (
    <>
      <div className="vs-wrap">
        <Side
          variant="old"
          title="Old way"
          subtitle="Screen-scraping & credential sharing"
          items={OLD}
        />
        <span className="vs-badge" aria-hidden="true">
          VS
        </span>
        <Side
          variant="new"
          title="New way — CDB Aggregator"
          subtitle="Consent-based data sharing"
          items={NEW}
        />
      </div>

      <div className="card principles">
        <h3>Principles behind the new model</h3>
        <div className="principles-grid">
          {PRINCIPLES.map(([icon, label]) => (
            <div key={label} className="principle">
              <span className="principle-icon">
                <Icon name={icon} />
              </span>
              <span>{label}</span>
            </div>
          ))}
        </div>
        <p className="section-note principles-note">
          These are the ideas the architecture is built to serve. It models the standard (FDX) on
          mock data — not a claim of live regulatory integration.
        </p>
      </div>
    </>
  );
}
