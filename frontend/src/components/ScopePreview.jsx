// Intent → scope preview (item-28): before a grant is minted, show exactly what
// the agent will and won't be able to see — consent as an informed choice, not a
// blind checkbox.
export default function ScopePreview({ preview }) {
  if (!preview) return null;
  const { agentName, durationDays, accountCount, visible, withheld } = preview;
  return (
    <div className="card scope-preview">
      <h3>Before you delegate</h3>
      <p className="section-note">
        {agentName} would get a {durationDays}-day grant over {accountCount} account
        {accountCount === 1 ? "" : "s"} — here is exactly what it could and couldn&apos;t read.
      </p>
      <div className="preview-cols">
        <div>
          <h4 className="preview-yes">Will be able to see</h4>
          <ul className="preview-list">
            {visible.map((s) => (
              <li key={s.scope}>
                <strong>{s.label}</strong>
                <span className="muted"> — {s.description}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="preview-no">Stays blind to</h4>
          <ul className="preview-list">
            {withheld.map((s) => (
              <li key={s.scope} className="withheld-row">
                <strong>{s.label}</strong>
                <span className="muted"> — {s.description}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
