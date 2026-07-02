import { useCallback, useEffect, useState } from "react";

import {
  decideApproval,
  delegateAgent,
  getActivity,
  getApprovals,
  getAuthority,
  getScopePreview,
  pauseAgent,
  resumeAgent,
  revokeDelegation,
  runAgent,
} from "../api.js";
import ActivityFeed from "../components/ActivityFeed.jsx";
import ApprovalQueue from "../components/ApprovalQueue.jsx";
import AssistantChat from "../components/AssistantChat.jsx";
import AuthorityCard from "../components/AuthorityCard.jsx";
import ScopePreview from "../components/ScopePreview.jsx";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { useToast } from "../components/Toaster.jsx";

// Poll cadence for the live action feed while the agent holds authority.
const POLL_MS = 3000;

// The assistant, in two views: Chat — a single conversation where you ask,
// delegate, and decide inline — and Activity — the authority console (item-28):
// the authority card, live action feed, approval queue, and scope preview.
const SUBTABS = [
  ["chat", "Chat"],
  ["activity", "Activity"],
];

export default function AgentPage({ scopeCatalog }) {
  const toast = useToast();
  const [sub, setSub] = useState("chat");
  const [authority, setAuthority] = useState(null);
  const [activity, setActivity] = useState(null);
  const [approvals, setApprovals] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [auth, feed, queue, prev] = await Promise.all([
      getAuthority(),
      getActivity(),
      getApprovals(),
      getScopePreview(),
    ]);
    setAuthority(auth);
    setActivity(feed);
    setApprovals(queue);
    setPreview(prev);
  }, []);

  useEffect(() => {
    refresh()
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [refresh]);

  // Live feed: poll only while the agent can act. Pausing or revoking flips
  // `live` false, which tears the interval down — the feed halts immediately.
  const live = activity?.live ?? false;
  useEffect(() => {
    if (!live) return undefined;
    const id = setInterval(() => {
      refresh().catch((err) => setError(String(err)));
    }, POLL_MS);
    return () => clearInterval(id);
  }, [live, refresh]);

  async function withBusy(fn, successMsg) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await refresh();
      if (successMsg) toast(successMsg);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  const onDelegate = () => withBusy(delegateAgent, "Task delegated to the assistant.");
  const onRevoke = () => withBusy(revokeDelegation, "Authority revoked — the agent stopped.");
  const onPause = () => withBusy(pauseAgent, "Agent paused.");
  const onResume = () => withBusy(resumeAgent, "Agent resumed.");
  const onRun = () => withBusy(runAgent, "Agent ran — a suggestion is awaiting your approval.");
  const onDecide = (id, decision) =>
    withBusy(() => decideApproval(id, { decision }), "Decision recorded.");

  const delegated = authority?.status === "GRANTED";

  return (
    <>
      {error && <div className="error">{error}</div>}

      <nav className="subtabs" aria-label="Assistant views">
        {SUBTABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={sub === key ? "active" : ""}
            aria-current={sub === key ? "page" : undefined}
            onClick={() => setSub(key)}
          >
            {label}
          </button>
        ))}
      </nav>

      {sub === "chat" &&
        (loading ? <SkeletonCard lines={8} /> : <AssistantChat authority={authority} refresh={refresh} />)}

      {sub === "activity" && (
        <div className="agent-cols">
          <section>
            <h2>Authority</h2>
            {loading ? (
              <SkeletonCard lines={5} />
            ) : (
              <>
                <AuthorityCard
                  authority={authority}
                  catalog={scopeCatalog}
                  busy={busy}
                  onDelegate={onDelegate}
                  onPause={onPause}
                  onResume={onResume}
                  onRevoke={onRevoke}
                  onRun={onRun}
                />
                {!delegated && <ScopePreview preview={preview} />}
              </>
            )}
          </section>

          <div className="console-main">
            {loading ? (
              <SkeletonCard lines={6} />
            ) : (
              <>
                <ActivityFeed activity={activity} catalog={scopeCatalog} />
                <ApprovalQueue approvals={approvals} onDecide={onDecide} busy={busy} />
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
