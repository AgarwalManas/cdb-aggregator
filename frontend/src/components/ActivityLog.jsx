import { useEffect, useMemo, useRef, useState } from "react";

import { formatDateTime } from "../format.js";

// Activity Log (slice 5): one table that merges the audit trail and the access
// receipts. Filter / sort / search, tick rows to select, expand any row into its
// full receipt, and export the selection in several formats. Driven entirely by
// /api/receipts, which already carries who / what / grant / disclosed / why.

const COLUMNS = [
  "Receipt",
  "When",
  "By",
  "Action",
  "Scope",
  "Account",
  "Decision",
  "Disclosed",
  "Withheld",
  "Grant",
];

function summaryRow(r) {
  return {
    Receipt: r.receiptId,
    When: r.occurredAt,
    By: r.accessorLabel,
    Action: r.purpose,
    Scope: r.clusterLabel,
    Account: r.accountId || "—",
    Decision: r.allowed ? "ALLOWED" : "DENIED",
    Disclosed: r.allowed ? String(r.recordCount) : "0",
    Withheld: r.withheld.join("; ") || "—",
    Grant: r.authorizingConsentId || "—",
  };
}

const download = (name, text, mime) => {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
};

const csvCell = (v) => `"${String(v).replace(/"/g, '""')}"`;
const mdCell = (v) => String(v).replace(/\|/g, "\\|");
const esc = (v) =>
  String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function toJSON(rows, enhanced) {
  return JSON.stringify(
    rows.map((r) => (enhanced ? r : summaryRow(r))),
    null,
    2,
  );
}

function toCSV(rows, enhanced) {
  const cols = enhanced ? [...COLUMNS, "Fields", "Why"] : COLUMNS;
  const header = cols.map(csvCell).join(",");
  const lines = rows.map((r) => {
    const s = summaryRow(r);
    const base = COLUMNS.map((c) => csvCell(s[c]));
    if (enhanced) base.push(csvCell(r.fields.join("; ")), csvCell(r.why));
    return base.join(",");
  });
  return [header, ...lines].join("\n");
}

function toMarkdown(rows, enhanced) {
  const header = `| ${COLUMNS.join(" | ")} |`;
  const rule = `| ${COLUMNS.map(() => "---").join(" | ")} |`;
  const body = rows.map((r) => {
    const s = summaryRow(r);
    return `| ${COLUMNS.map((c) => mdCell(s[c])).join(" | ")} |`;
  });
  let out = [header, rule, ...body].join("\n");
  if (enhanced) {
    out +=
      "\n\n## Receipt details\n\n" +
      rows
        .map((r) => `- **${r.receiptId}** — ${mdCell(r.why)} _(fields: ${r.fields.join(", ")})_`)
        .join("\n");
  }
  return out;
}

function printReceipts(rows, enhanced) {
  const win = window.open("", "_blank");
  if (!win) return;
  const head = COLUMNS.map((c) => `<th>${c}</th>`).join("");
  const body = rows
    .map((r) => {
      const s = summaryRow(r);
      const cells = COLUMNS.map((c) => `<td>${esc(s[c])}</td>`).join("");
      const detail = enhanced
        ? `<tr><td colspan="${COLUMNS.length}" class="d"><b>Why:</b> ${esc(r.why)}<br><b>Fields:</b> ${esc(r.fields.join(", "))}</td></tr>`
        : "";
      return `<tr>${cells}</tr>${detail}`;
    })
    .join("");
  win.document.write(
    `<html><head><title>Access receipts</title><style>body{font-family:system-ui,sans-serif;font-size:12px;padding:24px}h2{font-family:monospace}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:6px;text-align:left}th{background:#f2f2f2}.d{background:#fafafa;font-size:11px}</style></head><body><h2>Access receipts (${rows.length})</h2><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></body></html>`,
  );
  win.document.close();
  win.focus();
  win.print();
}

const EXPORTS = [
  ["Markdown (.md)", (rows, enh) => download("access-log.md", toMarkdown(rows, enh), "text/markdown")],
  ["CSV / Excel (.csv)", (rows, enh) => download("access-log.csv", toCSV(rows, enh), "text/csv")],
  ["JSON (.json)", (rows, enh) => download("access-log.json", toJSON(rows, enh), "application/json")],
  ["Print / Save as PDF", (rows, enh) => printReceipts(rows, enh)],
];

export default function ActivityLog({ receipts, catalog }) {
  const [actor, setActor] = useState("all");
  const [decision, setDecision] = useState("all");
  const [scope, setScope] = useState("all");
  const [query, setQuery] = useState("");
  const [sortDir, setSortDir] = useState("desc");
  const [selected, setSelected] = useState(() => new Set());
  const [openId, setOpenId] = useState(null);
  const [enhanced, setEnhanced] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menuOpen]);

  const scopes = useMemo(
    () => Array.from(new Set((receipts || []).map((r) => r.clusterLabel))).sort(),
    [receipts],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = (receipts || []).filter((r) => {
      if (actor !== "all" && r.accessorType !== actor) return false;
      if (decision === "allowed" && !r.allowed) return false;
      if (decision === "denied" && r.allowed) return false;
      if (scope !== "all" && r.clusterLabel !== scope) return false;
      if (q) {
        const hay = [r.purpose, r.accessorLabel, r.clusterLabel, r.accountId, r.why]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    const dir = sortDir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => (a.occurredAt < b.occurredAt ? -dir : a.occurredAt > b.occurredAt ? dir : 0));
  }, [receipts, actor, decision, scope, query, sortDir]);

  if (!receipts) return null;

  const exportRows = selected.size
    ? visible.filter((r) => selected.has(r.receiptId))
    : visible;
  const allSelected = visible.length > 0 && visible.every((r) => selected.has(r.receiptId));

  function toggleAll() {
    setSelected((prev) => {
      if (visible.every((r) => prev.has(r.receiptId))) return new Set();
      return new Set(visible.map((r) => r.receiptId));
    });
  }
  function toggleOne(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function clearFilters() {
    setActor("all");
    setDecision("all");
    setScope("all");
    setQuery("");
  }

  return (
    <div className="log">
      <div className="log-bar">
        <div className="log-controls">
          <select aria-label="Filter by actor" value={actor} onChange={(e) => setActor(e.target.value)}>
            <option value="all">All actors</option>
            <option value="aggregator">Aggregator</option>
            <option value="agent">Assistant</option>
            <option value="counterparty">Counterparty</option>
          </select>
          <select
            aria-label="Filter by decision"
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
          >
            <option value="all">All decisions</option>
            <option value="allowed">Allowed</option>
            <option value="denied">Denied</option>
          </select>
          <select aria-label="Filter by scope" value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="all">All scopes</option>
            {scopes.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <input
            type="search"
            className="log-search"
            placeholder="Search the log…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search the log"
          />
        </div>

        <div className="log-export">
          <label className="enhanced-toggle" title="Include full receipt detail in exports">
            <input type="checkbox" checked={enhanced} onChange={() => setEnhanced((v) => !v)} />
            Enhanced
          </label>
          <div className="export-wrap" ref={menuRef}>
            <button type="button" className="btn-revoke" onClick={() => setMenuOpen((v) => !v)}>
              Export {selected.size ? `(${selected.size})` : `(${visible.length})`} ▾
            </button>
            {menuOpen && (
              <div className="export-menu" role="menu">
                {EXPORTS.map(([label, fn]) => (
                  <button
                    key={label}
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      fn(exportRows, enhanced);
                      setMenuOpen(false);
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <p className="section-note export-hint">
        {selected.size
          ? `${selected.size} selected for export.`
          : "Tick rows to export a selection, or export everything shown."}{" "}
        Enhanced adds each receipt&apos;s fields and the &ldquo;why&rdquo; line.
      </p>

      {receipts.length === 0 ? (
        <p className="empty">No access recorded yet.</p>
      ) : visible.length === 0 ? (
        <p className="empty">
          No entries match these filters.{" "}
          <button type="button" className="link" onClick={clearFilters}>
            Clear filters
          </button>
          .
        </p>
      ) : (
        <div className="audit-scroll">
          <table className="audit activity-log-table">
            <thead>
              <tr>
                <th className="col-check">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    aria-label="Select all rows"
                  />
                </th>
                <th>
                  <button
                    type="button"
                    className="th-sort"
                    onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
                  >
                    When <span className="sort-caret" aria-hidden="true">{sortDir === "asc" ? "▲" : "▼"}</span>
                  </button>
                </th>
                <th>By</th>
                <th>Action</th>
                <th>Scope</th>
                <th>Account</th>
                <th>Decision</th>
                <th>Disclosed</th>
                <th>Grant</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((r) => {
                const open = openId === r.receiptId;
                return (
                  <FragmentRow
                    key={r.receiptId}
                    receipt={r}
                    open={open}
                    selected={selected.has(r.receiptId)}
                    catalog={catalog}
                    onToggleSelect={() => toggleOne(r.receiptId)}
                    onToggleOpen={() => setOpenId(open ? null : r.receiptId)}
                    enhanced={enhanced}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function FragmentRow({ receipt: r, open, selected, onToggleSelect, onToggleOpen, enhanced }) {
  return (
    <>
      <tr className={`${r.allowed ? "" : "denied"} ${open ? "row-open" : ""}`}>
        <td className="col-check">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggleSelect}
            aria-label={`Select ${r.receiptId}`}
          />
        </td>
        <td className="muted row-click" onClick={onToggleOpen}>
          <span className="row-caret" aria-hidden="true">{open ? "▾" : "▸"}</span>
          {formatDateTime(r.occurredAt)}
        </td>
        <td className="row-click" onClick={onToggleOpen}>
          {r.accessorType === "aggregator" ? (
            <span className="muted">Aggregator</span>
          ) : (
            <span className="by-agent">{r.accessorLabel}</span>
          )}
        </td>
        <td className="row-click" onClick={onToggleOpen}>{r.purpose}</td>
        <td className="row-click" onClick={onToggleOpen}>{r.clusterLabel}</td>
        <td className="muted row-click" onClick={onToggleOpen}>{r.accountId || "—"}</td>
        <td className="row-click" onClick={onToggleOpen}>
          {r.allowed ? (
            <span className="badge status-granted">Allowed</span>
          ) : (
            <span className="badge status-revoked">Denied</span>
          )}
        </td>
        <td className="muted row-click" onClick={onToggleOpen}>
          {r.allowed ? `${r.recordCount} record${r.recordCount === 1 ? "" : "s"}` : "—"}
          {r.withheld.length > 0 && <span className="withheld"> · withheld {r.withheld.join(", ")}</span>}
        </td>
        <td className="muted row-click" onClick={onToggleOpen}>
          <code>{r.authorizingConsentId || "—"}</code>
        </td>
      </tr>
      {open && (
        <tr className="detail-row">
          <td colSpan={9}>
            <div className="receipt-detail">
              <p className="receipt-why">{r.why}</p>
              <dl className="authority-meta">
                <div>
                  <dt>Fields in this cluster</dt>
                  <dd>{r.fields.join(", ") || "—"}</dd>
                </div>
                <div>
                  <dt>Authorizing grant</dt>
                  <dd>
                    <code>{r.authorizingConsentId || "—"}</code>
                  </dd>
                </div>
                <div>
                  <dt>Disclosed</dt>
                  <dd>
                    {r.allowed ? `${r.recordCount} record${r.recordCount === 1 ? "" : "s"}` : "nothing"}
                  </dd>
                </div>
                {r.withheld.length > 0 && (
                  <div>
                    <dt>Withheld</dt>
                    <dd>{r.withheld.join(", ")}</dd>
                  </div>
                )}
              </dl>
              <div className="detail-downloads">
                <button
                  type="button"
                  className="btn-revoke"
                  onClick={() => download(`${r.receiptId}.json`, toJSON([r], enhanced), "application/json")}
                >
                  Download JSON
                </button>
                <button
                  type="button"
                  className="btn-revoke"
                  onClick={() => download(`${r.receiptId}.md`, toMarkdown([r], enhanced), "text/markdown")}
                >
                  Download Markdown
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
