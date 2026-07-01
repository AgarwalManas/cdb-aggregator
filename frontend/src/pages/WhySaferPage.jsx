import Icon from "../components/Icon.jsx";

// Why this is safer (Trust & Privacy): the case for scoped, revocable,
// token-based access, as a grid of six. Copy kept honest for a demo — design and
// architecture claims, not unverifiable security assertions.
const CARDS = [
  [
    "shield",
    "You stay in control",
    "You decide what to share, for how long, and with whom. Nothing is permanent.",
  ],
  [
    "lock",
    "No credential sharing",
    "We never ask for your bank username or password. No screen-scraping, ever.",
  ],
  [
    "eye",
    "Full transparency",
    "See what data is shared, with whom, and when. Every access is logged and attributed.",
  ],
  [
    "refresh",
    "Easy to revoke",
    "Revoke access anytime and it ends immediately; grants also expire on their own.",
  ],
  [
    "shieldCheck",
    "Privacy by design",
    "Reads are minimized to the fields you granted — the rest is withheld, and shown as withheld.",
  ],
  [
    "badge",
    "Standards-aligned",
    "Built on open standards (FDX over OAuth 2.0 + FAPI), consent-first from the ground up.",
  ],
];

export default function WhySaferPage({ onNavigate }) {
  return (
    <>
      <div className="safer-grid">
        {CARDS.map(([icon, title, body]) => (
          <div key={title} className="card safer-card">
            <span className="safer-icon">
              <Icon name={icon} />
            </span>
            <h3>{title}</h3>
            <p className="section-note">{body}</p>
          </div>
        ))}
      </div>

      <div className="card trust-banner">
        <span className="tb-icon">
          <Icon name="lock" />
        </span>
        <div>
          <strong>Trust is the point, not a feature.</strong>
          <p className="section-note">
            The consent gate, the minimization, and the verifiable audit log are the product. See
            the contrast with the old way, or the principles behind the model.
          </p>
        </div>
        <button type="button" className="link" onClick={() => onNavigate("compare")}>
          Old vs New →
        </button>
      </div>
    </>
  );
}
