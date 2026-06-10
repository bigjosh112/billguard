"use client";

import { formatNaira, FinancialSummary } from "@/lib/api";

interface FinancialSummaryProps {
  summary: FinancialSummary | null;
  loading?: boolean;
}

export default function FinancialSummaryPanel({ summary, loading }: FinancialSummaryProps) {
  const maxCategorySpend = Math.max(
    ...(summary?.spending_by_category.map((c) => c.total) ?? [1]),
    1
  );

  return (
    <section>
      <div className="section-header">
        <p className="label-caps">Financial Summary</p>
      </div>
      <div className="p-5">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-[10px] bg-[var(--bg-elevated)] animate-pulse" />
            ))}
          </div>
        ) : !summary ? (
          <p className="text-[13px] text-[var(--text-muted)]">
            Upload a statement or seed demo data to see your summary.
          </p>
        ) : (
          <>
            {/* Metric cards */}
            <div className="grid grid-cols-3 gap-2 mb-5">
              {[
                { label: "Income", value: summary.total_inflow, color: "var(--accent-emerald)" },
                { label: "Spent", value: summary.total_outflow, color: "var(--accent-red)" },
                { label: "Net", value: summary.net, color: "var(--text-primary)" },
              ].map((card) => (
                <div
                  key={card.label}
                  className="rounded-[10px] bg-[var(--bg-elevated)] p-3"
                >
                  <p className="label-caps mb-1.5">{card.label}</p>
                  <p
                    className="font-mono text-[18px] font-bold leading-none"
                    style={{ color: card.color }}
                  >
                    {formatNaira(card.value)}
                  </p>
                </div>
              ))}
            </div>

            {/* Category breakdown */}
            {summary.spending_by_category.length > 0 && (
              <div>
                <p className="label-caps mb-3">Spending Breakdown</p>
                <div className="space-y-2.5">
                  {summary.spending_by_category.slice(0, 6).map((cat, i) => {
                    const pct = (cat.total / maxCategorySpend) * 100;
                    const opacity = Math.max(0.35, 1 - i * 0.12);
                    return (
                      <div key={cat.category}>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-[13px] text-[var(--text-secondary)] capitalize">
                            {cat.category.replace(/_/g, " ")}
                          </span>
                          <span className="font-mono text-[13px] text-[var(--text-primary)]">
                            {formatNaira(cat.total)}
                          </span>
                        </div>
                        <div className="h-[3px] rounded-full bg-[var(--bg-elevated)] overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${pct}%`,
                              background: `rgba(0, 200, 150, ${opacity})`,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
