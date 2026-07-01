import { useEffect, useRef, useState } from "react";

// User-verifiable audit log (item-30), as a compact top-right card (slice 5.1):
// the log is a SHA-256 hash chain, and the browser recomputes every link with Web
// Crypto to confirm nothing was altered. It auto-verifies on load (so "Verified
// intact" is earned, not asserted); the ▾ menu simulates tampering and exports
// the log + proof.

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function preimage(e, prevHash) {
  return [
    prevHash,
    e.occurredAt,
    e.action,
    e.customerId,
    e.recipient,
    e.scope,
    e.allowed ? "1" : "0",
    e.accountId || "",
    e.reason || "",
    e.consentId || "",
    String(e.recordCount),
    e.withheld.join(","),
  ].join("|");
}

async function recompute(chain) {
  let prev = chain.genesis;
  for (let i = 0; i < chain.entries.length; i += 1) {
    const e = chain.entries[i];
    if (e.prevHash !== prev) return { valid: false, brokenAt: i };
    if ((await sha256Hex(preimage(e, prev))) !== e.entryHash) return { valid: false, brokenAt: i };
    prev = e.entryHash;
  }
  const valid = prev === chain.head;
  return { valid, checked: chain.entries.length, brokenAt: valid ? null : chain.entries.length };
}

export default function ChainVerifier({ chain }) {
  const [result, setResult] = useState(null);
  const [tampered, setTampered] = useState(false);
  const [busy, setBusy] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    let alive = true;
    setTampered(false);
    if (chain) recompute(chain).then((r) => alive && setResult(r));
    return () => {
      alive = false;
    };
  }, [chain?.head]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menuOpen]);

  if (!chain) return null;

  async function onVerify() {
    setBusy(true);
    setTampered(false);
    setResult(await recompute(chain));
    setBusy(false);
  }
  async function onTamper() {
    setBusy(true);
    setTampered(true);
    setMenuOpen(false);
    const entries = chain.entries.map((e, i) =>
      i === 0 ? { ...e, recordCount: e.recordCount + 1 } : e,
    );
    setResult(await recompute({ ...chain, entries }));
    setBusy(false);
  }
  function onDownload() {
    const blob = new Blob([JSON.stringify(chain, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cdb-audit-chain.json";
    a.click();
    URL.revokeObjectURL(url);
    setMenuOpen(false);
  }

  const ok = result?.valid;
  const status =
    result == null
      ? "Checking…"
      : ok
        ? "Verified intact"
        : tampered
          ? `Caught a simulated tamper (entry ${result.brokenAt})`
          : "Chain broken";

  return (
    <div className={`log-integrity ${result && !ok ? "broken" : ""}`} ref={ref}>
      <div className="li-status">
        <span className="li-icon" aria-hidden="true">
          ◈
        </span>
        <div>
          <span className="li-title">Log integrity</span>
          <span className={`li-value ${ok ? "ok" : result ? "bad" : ""}`}>{status}</span>
        </div>
      </div>
      <div className="li-actions">
        <button type="button" className="btn-revoke" disabled={busy} onClick={onVerify}>
          Verify log integrity
        </button>
        <button
          type="button"
          className="li-more"
          aria-label="More integrity actions"
          onClick={() => setMenuOpen((v) => !v)}
        >
          ▾
        </button>
        {menuOpen && (
          <div className="export-menu li-menu" role="menu">
            <button type="button" role="menuitem" onClick={onTamper}>
              Simulate tampering
            </button>
            <button type="button" role="menuitem" onClick={onDownload}>
              Download log + proof
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
