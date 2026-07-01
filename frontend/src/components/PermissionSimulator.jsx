import { useEffect, useMemo, useState } from "react";

import { simulatePermissions } from "../api.js";

// Permission simulation (item-29): turn granting from a blind checkbox into an
// informed preview. Toggle candidate scopes and see exactly which fields you'd
// share vs keep private, computed against the mock data — before you grant.
function groupByCluster(fields) {
  const groups = {};
  fields.forEach((f) => {
    (groups[f.clusterLabel] ||= []).push(f);
  });
  return Object.entries(groups);
}

export default function PermissionSimulator({ scopeCatalog }) {
  const scopes = useMemo(() => Object.keys(scopeCatalog), [scopeCatalog]);
  const [selected, setSelected] = useState(() => new Set(["ACCOUNT_DETAILS"]));
  const [sim, setSim] = useState(null);

  useEffect(() => {
    let alive = true;
    simulatePermissions([...selected])
      .then((r) => {
        if (alive) setSim(r);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [selected]);

  function toggle(scope) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(scope)) next.delete(scope);
      else next.add(scope);
      return next;
    });
  }

  return (
    <div className="card simulator-card">
      <h3>Try a permission before you grant it</h3>
      <p className="section-note">
        Toggle scopes to preview exactly which fields you&apos;d share — and which stay private.
      </p>
      <fieldset className="scope-picker sim-scopes">
        <legend>Candidate scopes</legend>
        {scopes.map((s) => (
          <label key={s} className="scope-check">
            <input type="checkbox" checked={selected.has(s)} onChange={() => toggle(s)} />
            {scopeCatalog[s]?.label || s}
          </label>
        ))}
      </fieldset>

      {sim && (
        <div className="preview-cols">
          <div>
            <h4 className="preview-yes">Would be shared · {sim.visible.length}</h4>
            {sim.visible.length === 0 ? (
              <p className="muted">Nothing — no scope selected.</p>
            ) : (
              groupByCluster(sim.visible).map(([label, fields]) => (
                <div key={label} className="sim-group">
                  <span className="sim-cluster">{label}</span>
                  <ul className="preview-list">
                    {fields.map((f) => (
                      <li key={f.name}>
                        <strong>{f.name}</strong> <span className="muted">e.g. {f.example}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))
            )}
          </div>
          <div>
            <h4 className="preview-no">Stays private · {sim.withheld.length}</h4>
            {groupByCluster(sim.withheld).map(([label, fields]) => (
              <div key={label} className="sim-group">
                <span className="sim-cluster">{label}</span>
                <ul className="preview-list">
                  {fields.map((f) => (
                    <li key={f.name} className="withheld-row">
                      <strong>{f.name}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
