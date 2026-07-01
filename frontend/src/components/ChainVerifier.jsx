import { useEffect, useState } from "react";

// User-verifiable audit log (item-30): the traceability log is a SHA-256 hash
// chain, and this recomputes every link in the browser with Web Crypto — so the
// user confirms the log is intact themselves, rather than trusting the server's
// word. Also exports the log + proof for independent, offline verification.

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// The exact preimage the server hashed — mirrors backend hash_event().
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

  // A fresh chain (after a grant/revoke) invalidates any previous result.
  useEffect(() => {
    setResult(null);
    setTampered(false);
  }, [chain?.head]);

  if (!chain) return null;
  const shortHead = `${chain.head.slice(0, 10)}…${chain.head.slice(-8)}`;

  async function onVerify() {
    setBusy(true);
    setTampered(false);
    setResult(await recompute(chain));
    setBusy(false);
  }

  async function onSimulateTamper() {
    setBusy(true);
    setTampered(true);
    // Alter one record locally and prove the browser catches it — the server is
    // untouched; this only edits the copy in your tab.
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
  }

  return (
    <div className="card verifier">
      <div className="card-head">
        <h3>Verify it yourself</h3>
        <span className="badge chain chain-ok" title="The log is a SHA-256 hash chain">
          SHA-256
        </span>
      </div>
      <p className="section-note">
        Don&apos;t take the server&apos;s word for it. The log is a hash chain — your browser can
        recompute every link with Web Crypto and confirm nothing was altered.
      </p>
      <dl className="authority-meta">
        <div>
          <dt>Entries</dt>
          <dd>{chain.entries.length}</dd>
        </div>
        <div>
          <dt>Published head</dt>
          <dd>
            <code>{shortHead}</code>
          </dd>
        </div>
      </dl>
      <div className="verifier-actions">
        <button className="btn-primary" disabled={busy} onClick={onVerify}>
          Verify in your browser
        </button>
        <button className="btn-revoke" disabled={busy} onClick={onSimulateTamper}>
          Simulate tampering
        </button>
        <button className="btn-revoke" disabled={busy} onClick={onDownload}>
          Download log + proof
        </button>
      </div>
      {result && (
        <div className={`verify-result ${result.valid ? "ok" : "broken"}`}>
          {result.valid
            ? `Intact — ${result.checked} entries recomputed in your browser, and the head matches.`
            : tampered
              ? `Caught it — the altered record breaks the chain at entry ${result.brokenAt}. The real log is untouched.`
              : `Tampered — the chain breaks at entry ${result.brokenAt}.`}
        </div>
      )}
    </div>
  );
}
