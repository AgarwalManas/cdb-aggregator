import { useEffect, useRef, useState } from "react";

import {
  decideApproval,
  delegateAgent,
  getAccounts,
  getApprovals,
  getNetWorth,
  getTransactions,
  pauseAgent,
  resumeAgent,
  revokeDelegation,
  runAgent,
} from "../api.js";
import { formatDate, formatMoney } from "../format.js";
import AssistantSuggestion from "./AssistantSuggestion.jsx";
import Icon from "./Icon.jsx";

// A chat surface for the assistant — one conversation, scripted on purpose.
// Every answer is computed from the same consent-gated APIs the rest of the app
// uses (no LLM anywhere), and every agent read still lands in the audit trail.
// The conversation carries a visible context budget: past it, older turns are
// compressed into a summary line, the way a real agent manages its window.
export const CHAT_STORAGE_KEY = "cdb-assistant-chat";

const TOKEN_BUDGET = 500; // estimated tokens the "window" holds — small, so the demo shows itself
const KEEP_TAIL = 4; // never compress the most recent turns

const GREETING = {
  id: "greeting",
  role: "assistant",
  text:
    "Hi — I'm your household assistant. I'm a scripted demo (no LLM): I answer from your " +
    "consent-gated data, and I only ever suggest.\n\n" +
    "Try: “net worth”, “list my accounts”, “recent transactions”, or “find idle cash”.",
};

const HELP_TEXT =
  "I can answer a few things from your consented data:\n" +
  "• “net worth” — your household total, minus anything you haven't shared\n" +
  "• “list my accounts” — balances across your connected sources\n" +
  "• “recent transactions” — your latest activity\n" +
  "• “find idle cash” — I analyze and suggest; you approve or reject\n" +
  "• “pause”, “resume”, “revoke” — govern my authority right here";

const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function estimate(m) {
  const extra = m.suggestion ? JSON.stringify(m.suggestion).length : 0;
  return Math.ceil(((m.text || "").length + extra) / 4);
}

const totalTokens = (msgs) => msgs.reduce((n, m) => n + estimate(m), 0);

// Past the budget, fold everything but the newest turns into one summary line —
// the messages leave the window, not the record (that stays in Activity).
function compress(msgs) {
  if (totalTokens(msgs) <= TOKEN_BUDGET || msgs.length <= KEEP_TAIL + 1) return msgs;
  const cut = msgs.length - KEEP_TAIL;
  const prior = msgs[0]?.kind === "compressed" ? msgs[0] : null;
  const head = msgs.slice(0, cut).filter((m) => m.kind !== "compressed");
  if (!head.length) return msgs;
  const count = head.length + (prior?.count || 0);
  const saved = head.reduce((n, m) => n + estimate(m), 0) + (prior?.saved || 0);
  const topics = [
    ...new Set([
      ...(prior?.topics || []),
      ...head.filter((m) => m.role === "user" && m.topic).map((m) => m.topic),
    ]),
  ];
  return [
    {
      id: "compressed",
      role: "system",
      kind: "compressed",
      count,
      saved,
      topics,
      text:
        `Compressed ${count} earlier message${count === 1 ? "" : "s"} (≈${saved} tokens)` +
        (topics.length ? ` — topics: ${topics.join(", ")}` : "") +
        ". The full record stays in Activity.",
    },
    ...msgs.slice(cut),
  ];
}

const INTENTS = [
  ["networth", /net\s*worth|worth/, "net worth"],
  ["accounts", /account|balance/, "accounts"],
  ["transactions", /transaction|spend|recent/, "transactions"],
  ["idle", /idle|cash|yield|earn|suggest|run/, "idle cash"],
  ["delegate", /delegate|authori[sz]e|grant/, "authority"],
  ["revoke", /revoke|stop/, "authority"],
  ["pause", /pause/, "authority"],
  ["resume", /resume/, "authority"],
  ["help", /help|scope|access|permission|can you|what do/, "capabilities"],
];

function intentOf(text) {
  const t = text.toLowerCase();
  return INTENTS.find(([, re]) => re.test(t)) || ["unknown", null, null];
}

function loadMessages() {
  try {
    const raw = sessionStorage.getItem(CHAT_STORAGE_KEY);
    const parsed = raw && JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length) return parsed;
  } catch {
    /* fall through to a fresh chat */
  }
  return [GREETING];
}

export default function AssistantChat({ authority, refresh }) {
  const [messages, setMessages] = useState(loadMessages);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const threadRef = useRef(null);

  useEffect(() => {
    sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, pending]);

  const push = (...news) =>
    setMessages((prev) => compress([...prev, ...news.map((m) => ({ id: uid(), ...m }))]));

  const granted = authority?.status === "GRANTED";

  async function doDelegate() {
    await delegateAgent();
    await refresh();
    return {
      role: "assistant",
      text:
        "Done — I now hold 30-day, read-only authority over your consented accounts. " +
        "It's visible, pausable, and revocable in the Activity tab. Ask me to find idle cash.",
    };
  }

  async function respond(text) {
    const [intent] = intentOf(text);

    switch (intent) {
      case "networth": {
        const nw = await getNetWorth();
        const excluded = nw.excluded?.length || 0;
        return [
          {
            role: "assistant",
            text:
              `Your household net worth is ${formatMoney(nw.netWorth, nw.currency)} — assets ` +
              `${formatMoney(nw.assets, nw.currency)}, liabilities ${formatMoney(nw.liabilities, nw.currency)}.` +
              (excluded
                ? `\n\n${excluded} balance${excluded === 1 ? "" : "s"} you haven't shared ` +
                  "stayed out of this total — the consent gate working for you."
                : ""),
          },
        ];
      }

      case "accounts": {
        const accounts = await getAccounts();
        const lines = accounts
          .slice(0, 8)
          .map(
            (a) =>
              `• ${a.sourceLabel} — ${a.nickname || a.accountType}: ` +
              (a.balanceShared ? formatMoney(a.current, a.currency) : "balance not shared"),
          );
        const more = accounts.length > 8 ? `\n…and ${accounts.length - 8} more.` : "";
        return [
          {
            role: "assistant",
            text: `I can see ${accounts.length} accounts through your consents:\n${lines.join("\n")}${more}`,
          },
        ];
      }

      case "transactions": {
        const txns = await getTransactions();
        const lines = txns
          .slice(0, 3)
          .map(
            (t) =>
              `• ${t.description || "Transaction"} — ${t.direction === "CREDIT" ? "+" : "−"}` +
              `${formatMoney(t.amount, t.currency)} (${t.sourceLabel}, ${formatDate(t.occurredAt)})`,
          );
        return [
          {
            role: "assistant",
            text: `Your latest activity (of ${txns.length} transactions I can see):\n${lines.join("\n")}`,
          },
        ];
      }

      case "idle": {
        if (!granted) {
          return [
            {
              role: "assistant",
              text:
                "I don't hold authority yet, so I can't analyze anything. Delegate a scoped, " +
                "30-day read-only grant and I'll look for idle cash — I suggest, you decide.",
              actions: [{ id: "delegate", label: "Delegate read-only authority", primary: true }],
            },
          ];
        }
        if (authority.paused) {
          return [
            {
              role: "assistant",
              text: "I'm paused right now, so I'm not reading anything. Say “resume” first.",
            },
          ];
        }
        await runAgent();
        const approvals = await getApprovals();
        await refresh();
        const newest = approvals.filter((a) => a.status === "PENDING").at(-1);
        if (!newest) {
          return [
            { role: "assistant", text: "I ran the analysis but found nothing waiting on you." },
          ];
        }
        return [
          {
            role: "assistant",
            text:
              "I read your consented balances (each read is in the audit log) and found this. " +
              "It's a suggestion — nothing moves without you:",
          },
          {
            role: "assistant",
            kind: "suggestion",
            suggestion: newest.suggestion,
            approvalId: newest.approvalId,
          },
        ];
      }

      case "delegate": {
        if (granted) {
          return [
            {
              role: "assistant",
              text: "I already hold authority — ask me to find idle cash, or say “revoke” to end it.",
            },
          ];
        }
        return [await doDelegate()];
      }

      case "revoke": {
        if (!granted) {
          return [{ role: "assistant", text: "I hold no authority right now — nothing to revoke." }];
        }
        await revokeDelegation();
        await refresh();
        return [
          {
            role: "assistant",
            text: "Authority revoked — I can't read anything anymore. The record of what I did stays in Activity.",
          },
        ];
      }

      case "pause": {
        if (!granted) return [{ role: "assistant", text: "I hold no authority to pause." }];
        await pauseAgent();
        await refresh();
        return [{ role: "assistant", text: "Paused — I keep my grant but I stop acting until you say “resume”." }];
      }

      case "resume": {
        if (!granted) return [{ role: "assistant", text: "I hold no authority to resume." }];
        await resumeAgent();
        await refresh();
        return [{ role: "assistant", text: "Resumed — say “find idle cash” whenever you're ready." }];
      }

      case "help": {
        const scopes = granted ? `\n\nRight now I hold: ${authority.scopes.join(", ")}.` : "";
        return [{ role: "assistant", text: HELP_TEXT + scopes }];
      }

      default:
        return [
          {
            role: "assistant",
            text: "I'm a scripted demo, so that one's beyond me. " + HELP_TEXT,
          },
        ];
    }
  }

  async function handleSend(event) {
    event.preventDefault();
    send(input.trim());
  }

  async function send(q) {
    if (!q || pending) return;
    setInput("");
    const [, , topic] = intentOf(q);
    push({ role: "user", text: q, topic });
    setPending(true);
    const started = Date.now();
    let replies;
    try {
      replies = await respond(q);
    } catch (err) {
      replies = [{ role: "assistant", text: `Something went wrong: ${err}` }];
    }
    // A brief beat before answering — smoothness, not fake latency.
    await wait(Math.max(0, 550 - (Date.now() - started)));
    setPending(false);
    push(...replies);
  }

  async function handleAction(actionId) {
    if (pending) return;
    setPending(true);
    try {
      if (actionId === "delegate") push(await doDelegate());
    } catch (err) {
      push({ role: "assistant", text: `Something went wrong: ${err}` });
    } finally {
      setPending(false);
    }
  }

  async function decide(message, verb) {
    if (pending) return;
    setPending(true);
    try {
      await decideApproval(message.approvalId, { decision: verb });
      await refresh();
      setMessages((prev) =>
        prev.map((m) => (m.id === message.id ? { ...m, decided: verb } : m)),
      );
      push({
        role: "assistant",
        text:
          verb === "approve"
            ? "Recorded — approved. Reminder: I only suggest; the demo never moves money."
            : "Recorded — rejected. The suggestion stays on the record in Activity.",
      });
    } catch (err) {
      push({ role: "assistant", text: `Something went wrong: ${err}` });
    } finally {
      setPending(false);
    }
  }

  const used = totalTokens(messages);
  const pct = Math.min(100, Math.round((used / TOKEN_BUDGET) * 100));

  return (
    <div className="card chat-card">
      <div className="chat-head">
        <span className="chat-chip">Scripted demo · no LLM</span>
        <span className="chat-chip">1 conversation</span>
        <div className="chat-ctx" title="Estimated context window — older turns compress automatically past the budget">
          <span>
            context {used}/{TOKEN_BUDGET} tokens
          </span>
          <span className="ctx-bar" aria-hidden="true">
            <span className="ctx-fill" style={{ width: `${pct}%` }} />
          </span>
        </div>
        <button
          type="button"
          className="link chat-clear"
          onClick={() => setMessages([GREETING])}
        >
          Clear
        </button>
      </div>

      <div className="chat-thread" ref={threadRef}>
        {messages.map((m) => {
          if (m.kind === "compressed") {
            return (
              <div key={m.id} className="chat-sys">
                {m.text}
              </div>
            );
          }
          if (m.kind === "suggestion") {
            return (
              <div key={m.id} className="msg-suggestion">
                <AssistantSuggestion suggestion={m.suggestion} />
                {m.decided ? (
                  <p className="muted decided-line">
                    Recorded — {m.decided === "approve" ? "approved" : "rejected"}.
                  </p>
                ) : (
                  <div className="msg-actions">
                    <button
                      className="btn-primary"
                      disabled={pending}
                      onClick={() => decide(m, "approve")}
                    >
                      Approve
                    </button>
                    <button
                      className="btn-revoke"
                      disabled={pending}
                      onClick={() => decide(m, "reject")}
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            );
          }
          return (
            <div key={m.id} className={`msg ${m.role === "user" ? "user" : "assistant"}`}>
              {m.text}
              {m.actions && (
                <div className="msg-actions">
                  {m.actions.map((a) => (
                    <button
                      key={a.id}
                      className={a.primary ? "btn-primary" : "btn-revoke"}
                      disabled={pending}
                      onClick={() => handleAction(a.id)}
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {pending && (
          <div className="msg assistant">
            <span className="typing" aria-label="Assistant is responding">
              <i />
              <i />
              <i />
            </span>
          </div>
        )}
        {messages.length <= 1 && !pending && (
          <div className="chat-suggest">
            {[
              "What's my net worth?",
              "List my accounts",
              "Recent transactions",
              "Find idle cash",
            ].map((q) => (
              <button key={q} type="button" className="suggest-chip" onClick={() => send(q)}>
                {q}
              </button>
            ))}
          </div>
        )}
      </div>

      <form className="chat-composer" onSubmit={handleSend}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your money — or “find idle cash”…"
          aria-label="Message the assistant"
        />
        <button type="submit" className="btn-primary chat-send" disabled={pending || !input.trim()}>
          <Icon name="send" />
        </button>
      </form>
    </div>
  );
}
