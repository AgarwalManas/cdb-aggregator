import Icon from "../components/Icon.jsx";

// How it works (Trust & Privacy): the six-step journey through the product, each
// step deep-linking into the feature that does it. Doubles as the guided path
// for a first-time visitor.
const STEPS = [
  [
    "bank",
    "Connect a data source",
    "Connect a bank or provider through standards-based, token access — no passwords handed over.",
    "control",
    "Manage connections",
  ],
  [
    "sliders",
    "Choose what to share",
    "Grant consent with granular scopes: you decide what data, for how long, and for which accounts.",
    "control",
    "Review consents",
  ],
  [
    "layers",
    "See your combined view",
    "Your accounts from every source, merged into one picture — showing only what you allowed.",
    "accounts",
    "See Bank Accounts",
  ],
  [
    "sparkle",
    "Delegate to the Assistant",
    "Hand a scoped, revocable task to the agent. It reads only what you delegate, and suggests — never acts.",
    "assistant",
    "Open Assistant",
  ],
  [
    "shieldCheck",
    "Revoke anytime",
    "Change or revoke a connection whenever you like. Access ends immediately, and grants also expire on their own.",
    "control",
    "Manage access",
  ],
  [
    "fileCheck",
    "Verify every access",
    "Every read is logged and tied to the grant that permitted it — and you can recompute the log in your browser.",
    "control",
    "View activity log",
  ],
];

export default function HowItWorksPage({ onNavigate }) {
  return (
    <>
      <ol className="steps">
        {STEPS.map(([icon, title, body, dest, cta], i) => (
          <li key={title} className="card step">
            <div className="step-top">
              <span className="step-num">{i + 1}</span>
              <span className="step-icon">
                <Icon name={icon} />
              </span>
            </div>
            <h3>{title}</h3>
            <p className="section-note">{body}</p>
            <button type="button" className="link step-link" onClick={() => onNavigate(dest)}>
              {cta} →
            </button>
          </li>
        ))}
      </ol>

      <div className="card trust-banner">
        <span className="tb-icon">
          <Icon name="shieldCheck" />
        </span>
        <div>
          <strong>Your data is shown only with your consent.</strong>
          <p className="section-note">
            Every read passes the consent gate, comes back minimized to the fields you granted, and
            lands in an auditable trail you can verify yourself. (Demo data — this models the
            architecture, not a live bank integration.)
          </p>
        </div>
        <button type="button" className="link" onClick={() => onNavigate("safer")}>
          Why this is safer →
        </button>
      </div>
    </>
  );
}
