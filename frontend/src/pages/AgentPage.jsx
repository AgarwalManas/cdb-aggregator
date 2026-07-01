import { useCallback, useEffect, useState } from "react";

import { delegateAgent, getDelegation, revokeDelegation, runAgent } from "../api.js";
import AssistantSuggestion from "../components/AssistantSuggestion.jsx";
import DelegationCard from "../components/DelegationCard.jsx";

// The agentic delegation / intent layer (Item 11): delegate a scoped, revocable,
// logged task to the agent, run it, and see its suggestion.
export default function AgentPage({ scopeCatalog }) {
  const [delegation, setDelegation] = useState(null);
  const [suggestion, setSuggestion] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const del = await getDelegation();
    setDelegation(del);
    if (del.status === "GRANTED") {
      setSuggestion(await runAgent());
    } else {
      setSuggestion(null);
    }
  }, []);

  useEffect(() => {
    load().catch((err) => setError(String(err)));
  }, [load]);

  async function withBusy(fn) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  const onDelegate = () => withBusy(delegateAgent);
  const onRevoke = () => withBusy(revokeDelegation);
  const onRun = () => withBusy(async () => setSuggestion(await runAgent()));

  return (
    <>
      {error && <div className="error">{error}</div>}

      <div className="agent-cols">
        <section>
          <h2>Delegated assistant</h2>
          <p className="section-note">
            A task delegated to an agent is just another consent — scoped, time-limited, and
            revocable. Everything it reads is logged against the agent in your traceability log.
          </p>
          <DelegationCard
            delegation={delegation}
            catalog={scopeCatalog}
            onDelegate={onDelegate}
            onRevoke={onRevoke}
            busy={busy}
          />
        </section>

        <section>
          <div className="suggestion-head">
            <h2>Suggestion</h2>
            {delegation?.status === "GRANTED" && (
              <button className="btn-primary" disabled={busy} onClick={onRun}>
                Run again
              </button>
            )}
          </div>
          {delegation?.status === "GRANTED" ? (
            <AssistantSuggestion suggestion={suggestion} />
          ) : (
            <div className="card">
              <p className="empty">
                The assistant has no active delegation, so it can&apos;t see anything. Delegate the
                task to let it look.
              </p>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
