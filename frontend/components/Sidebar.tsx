"use client";

import { Zap } from "lucide-react";
import { FinancialSummary, formatNaira, clearSession } from "@/lib/api";

interface SidebarProps {
  summary: FinancialSummary | null;
  loading?: boolean;
}

export default function Sidebar({ summary, loading }: SidebarProps) {
  const income = summary?.total_inflow ?? 0;
  const spending = summary?.total_outflow ?? 0;
  const net = summary?.net ?? 0;
  const billsDue = summary?.total_bills_due ?? 0;
  const salaryAmount = summary?.salary?.amount ?? (income || 450000);
  const billsPct = salaryAmount > 0 ? Math.min((billsDue / salaryAmount) * 100, 100) : 0;

  const stats = [
    { icon: "💰", label: "Income", value: formatNaira(income), color: "var(--accent-emerald)" },
    { icon: "📤", label: "Spending", value: formatNaira(spending), color: "var(--accent-red)" },
    { icon: "📊", label: "Net", value: formatNaira(net), color: "var(--text-primary)" },
  ];

  return (
    <aside
      className="hidden lg:flex flex-col w-[280px] shrink-0 h-screen sticky top-0 border-r border-[var(--bg-border)] bg-[var(--bg-surface)] p-6 animate-page-enter opacity-0"
      style={{ animationFillMode: "forwards" }}
    >
      {/* Logo */}
      <div>
        <div className="flex items-center gap-2">
          <span className="text-xl">🛡️</span>
          <span className="text-[18px] font-bold tracking-[-0.5px] text-[var(--text-primary)]">
            BillGuard
          </span>
        </div>
        <p className="label-caps mt-1">AI Finance Agent</p>
      </div>

      <div className="h-px bg-[var(--bg-border)] my-5" />

      {/* Quick Stats */}
      <div>
        <p className="label-caps mb-3">This Month</p>
        <div className="space-y-1">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg text-[13px] transition-colors duration-150 hover:bg-[var(--bg-elevated)] cursor-default"
            >
              <span className="flex items-center gap-2 text-[var(--text-secondary)]">
                <span>{stat.icon}</span>
                {stat.label}
              </span>
              <span
                className="font-mono text-[14px] font-semibold"
                style={{ color: loading ? "var(--text-muted)" : stat.color }}
              >
                {loading ? "—" : stat.value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Bills progress */}
      <div className="mt-5">
        <div className="flex justify-between items-center mb-2 text-[12px]">
          <span className="text-[var(--text-secondary)]">Bills Due</span>
          <span className="font-mono font-semibold text-[var(--accent-amber)]">
            {loading ? "—" : formatNaira(billsDue)}
          </span>
        </div>
        <div className="h-1 rounded-full bg-[var(--bg-elevated)] overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: loading ? "0%" : `${billsPct}%`,
              background: "linear-gradient(90deg, var(--accent-amber), var(--accent-red))",
            }}
          />
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Start fresh */}
      <button
        type="button"
        onClick={() => {
          if (confirm("Clear all your data and start fresh?")) {
            clearSession();
            window.location.reload();
          }
        }}
        className="mb-3 w-full rounded-lg border border-[var(--bg-border)] py-2 text-xs text-[var(--text-muted)] transition-colors hover:border-red-400/30 hover:text-red-400"
      >
        🗑 Start Fresh
      </button>

      {/* Powered by badge */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-md border border-[var(--brand)] bg-[var(--brand-dim)]">
        <Zap size={12} className="text-[var(--brand)] shrink-0" />
        <span className="text-[11px] text-[var(--brand)] leading-tight">
          Powered by Gemini 2.0 Flash + MongoDB
        </span>
      </div>
    </aside>
  );
}
