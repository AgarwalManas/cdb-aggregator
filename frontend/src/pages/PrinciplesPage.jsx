// "Consent principles" (slice 4): FDX's five principles, each with how this app
// makes it tangible and a link to where you can see it.
const PRINCIPLES = [
  [
    "Control",
    "You decide who sees what, and for how long — granular scopes you grant and revoke at will.",
    "control",
    "Manage in Control Centre",
  ],
  [
    "Access",
    "Standards-native, token-based access (FDX over OAuth 2.0 + FAPI) instead of shared credentials.",
    "compare",
    "See Old vs New",
  ],
  [
    "Transparency",
    "Every access is legible: a plain-language receipt of who read what, under which grant, and why.",
    "control",
    "Read your receipts",
  ],
  [
    "Traceability",
    "An append-only, hash-chained log — which you can recompute in your own browser to prove it's intact.",
    "control",
    "Verify integrity",
  ],
  [
    "Security · minimization",
    "Only the fields your granted scopes permit ever leave; the rest is withheld, and shown as withheld.",
    "accounts",
    "See minimization at work",
  ],
];

export default function PrinciplesPage({ onNavigate }) {
  return (
    <>
      <p className="section-note console-intro">
        FDX — the technical standard behind Canada&apos;s Consumer-Driven Banking — rests on five
        principles. The whole app is built to make each one tangible, not merely stated.
      </p>
      <div className="explain-grid">
        {PRINCIPLES.map(([title, body, dest, cta]) => (
          <div key={title} className="card explain-card">
            <h3>{title}</h3>
            <p className="section-note">{body}</p>
            <button type="button" className="link" onClick={() => onNavigate(dest)}>
              {cta} →
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
