import { formatDateTime, formatMoney } from "../format.js";
import AssistantSuggestion from "./AssistantSuggestion.jsx";

// The approval queue (item-28): the agent only ever *suggests*, so every run
// lands here awaiting a human decision — Approve / Reject / Request changes.
// Approving executes nothing; the queue makes the human-in-the-loop step a
// first-class, recorded object.
const DECISIONS = [
  ["approve", "Approve", "btn-primary"],
  ["request_changes", "Request changes", "btn-revoke"],
  ["reject", "Reject", "btn-revoke"],
];

const STATUS_LABEL = {
  PENDING: "Pending",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  CHANGES_REQUESTED: "Changes requested",
};

const STATUS_BADGE = {
  PENDING: "pending",
  APPROVED: "granted",
  REJECTED: "revoked",
  CHANGES_REQUESTED: "expired",
};

export default function ApprovalQueue({ approvals, onDecide, busy }) {
  if (!approvals) return null;
  return (
    <section className="approvals-section">
      <h2>Approvals</h2>
      {approvals.length === 0 ? (
        <div className="card">
          <p className="empty">Nothing awaiting a decision.</p>
        </div>
      ) : (
        <>
          <p className="section-note">
            The agent suggests; it never acts. Every run lands here for your decision — a human in
            the loop, on the record.
          </p>
          {approvals.map((a) => (
            <ApprovalCard key={a.approvalId} approval={a} onDecide={onDecide} busy={busy} />
          ))}
        </>
      )}
    </section>
  );
}

function ApprovalCard({ approval, onDecide, busy }) {
  const { approvalId, status, note, suggestion, createdAt } = approval;
  const pending = status === "PENDING";
  const s = suggestion;
  return (
    <div className={`card approval ${pending ? "" : "decided"}`}>
      <div className="card-head">
        <h3>
          {formatMoney(s.idleCash, s.currency)} idle · +{formatMoney(s.estimatedAnnualGain, s.currency)}
          /yr
        </h3>
        <span className={`badge status-${STATUS_BADGE[status]}`}>{STATUS_LABEL[status]}</span>
      </div>
      <p className="section-note">
        Suggested {formatDateTime(createdAt)} · {s.analyzed.length} account
        {s.analyzed.length === 1 ? "" : "s"} analyzed
      </p>

      {pending ? (
        <>
          <AssistantSuggestion suggestion={s} />
          <div className="approval-actions">
            {DECISIONS.map(([verb, label, cls]) => (
              <button
                key={verb}
                className={cls}
                disabled={busy}
                onClick={() => onDecide(approvalId, verb)}
              >
                {label}
              </button>
            ))}
          </div>
        </>
      ) : (
        <p className="muted decided-line">
          {STATUS_LABEL[status]}
          {note ? ` — “${note}”` : ""}.
        </p>
      )}
    </div>
  );
}
