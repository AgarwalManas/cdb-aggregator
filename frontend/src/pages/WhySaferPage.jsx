// "Why this is safer" (slice 4): the security argument for token-based, scoped
// access over credential screen-scraping. Complements the interactive Old vs New
// comparison with the plain reasoning.
const REASONS = [
  [
    "Your password stays at your bank",
    "Screen-scraping needs your online-banking login and signs in as you. Token-based access authorises a scoped token instead — the aggregator never sees or stores your password.",
  ],
  [
    "Least privilege, by design",
    "A login is all-or-nothing. Here, access is granted one scope at a time — account details, balances, transactions — so a tool only ever gets what it actually needs.",
  ],
  [
    "Revocation that actually works",
    "With shared credentials the only real off-switch is changing your password. Here, one tap revokes a connection and access stops immediately; grants also expire on their own.",
  ],
  [
    "A record you can trust",
    "There's no audit trail behind a scraper. Every access here — allowed or denied — is logged to an append-only, hash-chained trail you can re-verify in your own browser.",
  ],
  [
    "Nothing brittle to break",
    "Scrapers parse HTML and shatter when a bank restyles a page. This speaks a stable API contract (FDX), so the connection doesn't silently break.",
  ],
];

export default function WhySaferPage({ onNavigate }) {
  return (
    <>
      <p className="section-note console-intro">
        Most account aggregation in Canada still runs on screen-scraping — you give an app your bank
        login and it signs in as you. This app is built the other way: scoped, revocable, token-based
        access with a verifiable record. Five reasons that&apos;s safer.
      </p>
      <div className="explain-grid">
        {REASONS.map(([title, body], i) => (
          <div key={title} className="card explain-card">
            <span className="explain-num">{i + 1}</span>
            <h3>{title}</h3>
            <p className="section-note">{body}</p>
          </div>
        ))}
      </div>
      <p className="section-note">
        See the full side-by-side on{" "}
        <button type="button" className="link" onClick={() => onNavigate("compare")}>
          Old vs New
        </button>
        .
      </p>
    </>
  );
}
