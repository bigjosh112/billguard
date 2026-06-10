"use client";

import { useEffect, useState } from "react";

const THINKING_MESSAGES = [
  "Connecting to BillGuard…",
  "Reading your question…",
  "Pulling data from MongoDB…",
  "Analysing your transactions…",
  "Checking spending patterns…",
  "Running the numbers…",
  "Preparing your insight…",
];

interface ThinkingIndicatorProps {
  statusMessage?: string | null;
  phase?: string | null;
}

export default function ThinkingIndicator({ statusMessage, phase }: ThinkingIndicatorProps) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (statusMessage) return;
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % THINKING_MESSAGES.length);
    }, 2200);
    return () => clearInterval(timer);
  }, [statusMessage]);

  const displayMessage = statusMessage || THINKING_MESSAGES[index];

  return (
    <div className="flex justify-start animate-fade-in-up">
      <div
        className="flex items-center gap-3 px-4 py-3 rounded-[4px_18px_18px_18px] border border-[var(--bg-border)] bg-[var(--bg-surface)]"
        style={{ borderLeft: "3px solid var(--accent-purple)" }}
      >
        <span className="relative flex h-3 w-3 shrink-0">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--accent-purple)] opacity-40" />
          <span className="relative inline-flex rounded-full h-3 w-3 bg-[var(--accent-purple)]" />
        </span>
        <div>
          <p className="text-[13px] text-[var(--text-secondary)]">{displayMessage}</p>
          {phase === "writing" && (
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">Composing response…</p>
          )}
          {phase === "finishing" && (
            <p className="text-[11px] text-[var(--brand)] mt-0.5">Almost done…</p>
          )}
        </div>
      </div>
    </div>
  );
}
