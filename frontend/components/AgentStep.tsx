"use client";

import { Check, Loader2, X } from "lucide-react";

export interface AgentStepData {
  id: string;
  tool: string;
  status: "loading" | "complete" | "error";
  message: string;
  summary?: string;
}

interface AgentStepProps {
  step: AgentStepData;
  index?: number;
}

export default function AgentStep({ step, index = 0 }: AgentStepProps) {
  const isLoading = step.status === "loading";
  const isComplete = step.status === "complete";
  const displayText = isComplete ? step.summary || step.message : step.message;

  return (
    <div
      className="flex items-start gap-2 rounded-r-lg bg-[var(--bg-surface)]/50 px-3 py-2 text-xs animate-fade-in-up opacity-0"
      style={{
        borderLeft: `2px solid ${
          isLoading
            ? "rgba(168, 85, 247, 0.6)"
            : isComplete
              ? "rgba(16, 185, 129, 0.6)"
              : "rgba(239, 68, 68, 0.6)"
        }`,
        animationDelay: `${index * 80}ms`,
        animationFillMode: "forwards",
      }}
    >
      {isLoading && (
        <Loader2 size={12} className="mt-0.5 shrink-0 animate-spin text-purple-400" />
      )}
      {isComplete && (
        <Check size={12} className="mt-0.5 shrink-0 text-emerald-400" />
      )}
      {step.status === "error" && (
        <X size={12} className="mt-0.5 shrink-0 text-red-400" />
      )}
      <span className="leading-relaxed text-[var(--text-muted)]">
        {isComplete && displayText && !displayText.startsWith("✓") ? `✓ ${displayText}` : displayText}
      </span>
    </div>
  );
}
