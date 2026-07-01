// A placeholder for the "How it works" explainers (slice 1). These pages —
// "Why this is safer" and "Consent principles" — get real content in a later
// pass; for now they're honest stubs so the navigation structure is complete.
export default function ExplainerPage({ title, blurb }) {
  return (
    <div className="card stub-hero">
      <h2>{title}</h2>
      <p className="section-note">{blurb}</p>
      <p className="muted">This explainer is being written — it lands in a later pass.</p>
    </div>
  );
}
