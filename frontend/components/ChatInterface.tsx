"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { ArrowUp } from "lucide-react";
import { streamChat, ChatStreamEvent, getSessionId } from "@/lib/api";
import { useToast } from "@/components/Toast";
import AgentStep, { AgentStepData } from "./AgentStep";
import MarkdownMessage from "./MarkdownMessage";
import ThinkingIndicator from "./ThinkingIndicator";

type MessageItem =
  | { type: "user"; id: string; content: string }
  | { type: "agent"; id: string; content: string; steps: AgentStepData[] };

const SUGGESTED_PROMPTS = [
  "I have ₦87,000. What do I pay first?",
  "Will I make it to my next payday?",
  "My rent is ₦120,000 due June 1st",
  "I earn ₦450,000, paid on the 25th",
  "What subscriptions can I cancel?",
  "Show me where my money is going",
];

interface ChatInterfaceProps {
  sessionId?: string;
  onDataChanged?: () => void;
}

export default function ChatInterface({ sessionId, onDataChanged }: ChatInterfaceProps) {
  const [activeSessionId, setActiveSessionId] = useState(sessionId ?? "default");

  useEffect(() => {
    if (!sessionId) {
      setActiveSessionId(getSessionId());
    }
  }, [sessionId]);

  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusPhase, setStatusPhase] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sendingRef = useRef(false);
  const { showToast } = useToast();

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const updateAgentMessage = useCallback(
    (agentId: string, updater: (msg: Extract<MessageItem, { type: "agent" }>) => MessageItem) => {
      setMessages((prev) =>
        prev.map((m) => (m.type === "agent" && m.id === agentId ? updater(m as Extract<MessageItem, { type: "agent" }>) : m))
      );
    },
    []
  );

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming || sendingRef.current) return;

    sendingRef.current = true;
    const userMessage = trimmed;
    const agentId = `agent-${Date.now()}`;

    setInput("");
    setIsStreaming(true);
    setStatusMessage("Connecting to BillGuard…");
    setStatusPhase("connecting");

    setMessages((prev) => [
      ...prev,
      { type: "user", id: `user-${Date.now()}`, content: userMessage },
      { type: "agent", id: agentId, content: "", steps: [] },
    ]);
    scrollToBottom();

    try {
      await streamChat(userMessage, activeSessionId, (event: ChatStreamEvent) => {
        if (event.type === "status") {
          setStatusMessage(event.message || null);
          setStatusPhase(event.phase || null);
          scrollToBottom();
        }

        if (event.type === "tool_call" && event.tool) {
          setStatusMessage(null);
          const step: AgentStepData = {
            id: `${event.tool}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            tool: event.tool,
            status: "loading",
            message: event.message || `Running ${event.tool}`,
          };
          updateAgentMessage(agentId, (msg) => ({
            ...msg,
            steps: [...msg.steps, step],
          }));
          scrollToBottom();
        }

        if (event.type === "tool_result" && event.tool) {
          updateAgentMessage(agentId, (msg) => {
            const steps = [...msg.steps];
            for (let i = steps.length - 1; i >= 0; i--) {
              if (steps[i].tool === event.tool && steps[i].status === "loading") {
                steps[i] = {
                  ...steps[i],
                  status: "complete",
                  summary: event.result_summary || steps[i].message,
                };
                break;
              }
            }
            return { ...msg, steps };
          });

          if (
            event.tool === "save_bill_from_chat" ||
            event.tool === "save_salary_from_chat" ||
            event.tool === "prioritise_bills" ||
            event.tool === "mark_bill_paid_from_chat"
          ) {
            onDataChanged?.();
          }

          if (
            event.tool === "mark_bill_paid_from_chat" &&
            event.result_summary &&
            !event.result_summary.startsWith("Error")
          ) {
            showToast(event.result_summary, "success");
          }

          scrollToBottom();
        }

        if (event.type === "text" && event.content) {
          setStatusMessage(null);
          updateAgentMessage(agentId, (msg) => ({
            ...msg,
            content: msg.content + event.content,
          }));
          scrollToBottom();
        }

        if (event.type === "error") {
          const errText = event.content || "Something went wrong.";
          updateAgentMessage(agentId, (msg) => ({
            ...msg,
            content: errText,
            steps: msg.steps.map((s) =>
              s.status === "loading" ? { ...s, status: "error" as const } : s
            ),
          }));
          setStatusMessage(null);
        }

        if (event.type === "done") {
          setStatusMessage(null);
          setStatusPhase(null);
        }
      });
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Chat failed — is the backend running?";
      updateAgentMessage(agentId, (msg) => ({
        ...msg,
        content: `⚠️ ${errMsg}`,
      }));
      setStatusMessage(null);
    } finally {
      setIsStreaming(false);
      setStatusPhase(null);
      setStatusMessage(null);
      sendingRef.current = false;
    }
  };

  const shortSessionId = activeSessionId.slice(0, 12);
  const activeAgent = [...messages].reverse().find((m) => m.type === "agent");
  const showThinking =
    isStreaming &&
    activeAgent?.type === "agent" &&
    !activeAgent.content &&
    activeAgent.steps.length === 0;

  return (
    <div className="flex flex-col h-full min-h-0 bg-[var(--bg-base)]">
      <header className="shrink-0 h-14 flex items-center justify-between px-6 border-b border-[var(--bg-border)] bg-[var(--bg-surface)]">
        <div className="flex items-center gap-2.5">
          <span className="text-[14px] font-semibold text-[var(--text-primary)]">
            BillGuard Agent
          </span>
          <span
            className={`w-2 h-2 rounded-full animate-pulse-dot ${isStreaming ? "bg-[var(--accent-amber)]" : "bg-[var(--brand)]"}`}
          />
          <span className="text-[12px]" style={{ color: isStreaming ? "var(--accent-amber)" : "var(--brand)" }}>
            {isStreaming ? "Thinking…" : "Online"}
          </span>
        </div>
        <span className="font-mono text-[11px] px-2 py-1 rounded-md bg-[var(--bg-elevated)] text-[var(--text-muted)] border border-[var(--bg-border)]">
          {shortSessionId}
        </span>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6 min-h-0">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full min-h-[280px]">
            <p className="text-[15px] text-[var(--text-secondary)] text-center mb-8">
              Ask BillGuard anything about your finances
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  disabled={isStreaming}
                  onClick={() => sendMessage(prompt)}
                  className="px-[18px] py-2.5 rounded-full text-[13px] text-[var(--text-secondary)] border border-[var(--bg-border)] bg-[var(--bg-surface)] cursor-pointer transition-all duration-200 hover:border-[var(--brand)] hover:text-[var(--text-primary)] hover:bg-[var(--brand-dim)] hover:scale-[1.02] disabled:opacity-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {messages.map((msg, i) => {
            if (msg.type === "user") {
              return (
                <div
                  key={msg.id}
                  className="flex justify-end animate-fade-in-up opacity-0"
                  style={{ animationDelay: `${i * 50}ms`, animationFillMode: "forwards" }}
                >
                  <div
                    className="max-w-[75%] px-4 py-3 text-[14px] leading-relaxed rounded-[18px_18px_4px_18px] mb-2"
                    style={{
                      background: "linear-gradient(135deg, #00C896, #00A87A)",
                      color: "#080B14",
                    }}
                  >
                    {msg.content}
                  </div>
                </div>
              );
            }

            return (
              <div
                key={msg.id}
                className="flex flex-col items-start max-w-[85%] animate-fade-in-up opacity-0"
                style={{ animationDelay: `${i * 50}ms`, animationFillMode: "forwards" }}
              >
                {msg.steps.length > 0 && (
                  <div className="w-full space-y-1.5 mb-2">
                    {msg.steps.map((step, si) => (
                      <AgentStep key={step.id} step={step} index={si} />
                    ))}
                  </div>
                )}

                {msg.content && (
                  <div className="px-4 py-4 text-[14px] leading-[1.7] rounded-[4px_18px_18px_18px] mb-2 border border-[var(--bg-border)] bg-[var(--bg-surface)] text-[var(--text-primary)] agent-markdown">
                    <MarkdownMessage content={msg.content} />
                    {isStreaming && msg.id === activeAgent?.id && (
                      <span className="inline-block w-0.5 h-4 bg-[var(--brand)] ml-0.5 animate-pulse align-middle" />
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {showThinking && (
            <ThinkingIndicator statusMessage={statusMessage} phase={statusPhase} />
          )}
        </div>

        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage(input);
        }}
        className="shrink-0 flex items-center gap-3 px-6 py-4 border-t border-[var(--bg-border)] bg-[var(--bg-surface)]"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isStreaming ? "BillGuard is thinking…" : "Ask about your finances..."}
          disabled={isStreaming}
          className="flex-1 input-dark rounded-xl py-3.5 px-4 text-[14px] disabled:opacity-50"
          style={{ boxShadow: "none" }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = "var(--brand)";
            e.currentTarget.style.boxShadow = "0 0 0 3px var(--brand-glow)";
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = "var(--bg-border)";
            e.currentTarget.style.boxShadow = "none";
          }}
        />
        <button
          type="submit"
          disabled={isStreaming || !input.trim()}
          className="shrink-0 w-11 h-11 flex items-center justify-center rounded-[10px] transition-all duration-200 disabled:scale-100 hover:enabled:scale-105"
          style={{
            background: isStreaming || !input.trim() ? "var(--bg-elevated)" : "var(--brand)",
            color: isStreaming || !input.trim() ? "var(--text-muted)" : "#080B14",
          }}
        >
          <ArrowUp size={18} strokeWidth={2.5} />
        </button>
      </form>
      <p
        className="text-center pb-3 px-6"
        style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}
      >
        You can add bills and salary info directly in the chat
      </p>
    </div>
  );
}
