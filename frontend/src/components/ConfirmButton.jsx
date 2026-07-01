import { useState } from "react";

// A destructive action with an inline confirm step (no modal): the first click
// arms it, the second confirms, and Cancel backs out. Revoking access should
// take a deliberate second tap.
export default function ConfirmButton({ label, confirmLabel, onConfirm, busy, className = "btn-revoke" }) {
  const [armed, setArmed] = useState(false);

  if (!armed) {
    return (
      <button className={className} disabled={busy} onClick={() => setArmed(true)}>
        {label}
      </button>
    );
  }

  return (
    <div className="confirm-row">
      <button
        className={className}
        disabled={busy}
        onClick={() => {
          setArmed(false);
          onConfirm();
        }}
      >
        {confirmLabel}
      </button>
      <button className="btn-ghost" disabled={busy} onClick={() => setArmed(false)}>
        Cancel
      </button>
    </div>
  );
}
