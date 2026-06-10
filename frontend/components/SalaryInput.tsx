"use client";

import { useEffect, useState } from "react";
import { Calendar } from "lucide-react";
import { FinancialSummary, setSalary, formatNaira } from "@/lib/api";

interface SalaryInputProps {
  summary: FinancialSummary | null;
  onSaved?: () => void;
}

export default function SalaryInput({ summary, onSaved }: SalaryInputProps) {
  const [amount, setAmount] = useState("");
  const [payDate, setPayDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (summary?.salary) {
      setAmount(String(summary.salary.amount));
      setPayDate(summary.salary.pay_date);
    }
  }, [summary]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !payDate) return;

    setSaving(true);
    setSaved(false);
    try {
      await setSalary({ amount: Number(amount), pay_date: payDate });
      setSaved(true);
      onSaved?.();
    } finally {
      setSaving(false);
    }
  };

  return (
    <section>
      <div className="section-header">
        <p className="label-caps">Salary Info</p>
      </div>
      <div className="p-5">
        <form onSubmit={handleSave} className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] text-[13px]">
                ₦
              </span>
              <input
                type="number"
                placeholder="450,000"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="input-dark w-full pl-7 font-mono"
              />
            </div>
            <div className="relative">
              <input
                type="date"
                value={payDate}
                onChange={(e) => setPayDate(e.target.value)}
                className="input-dark w-full font-mono pr-8"
              />
              <Calendar
                size={14}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full py-[11px] rounded-lg text-[13px] font-semibold transition-all duration-200 disabled:opacity-50"
            style={{
              background: "var(--brand)",
              color: "#080B14",
            }}
            onMouseEnter={(e) => {
              if (!saving) e.currentTarget.style.background = "var(--brand-hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "var(--brand)";
            }}
          >
            {saving ? "Saving…" : "Save Salary"}
          </button>

          {saved && (
            <p className="text-[11px] text-[var(--accent-emerald)] font-mono text-center">
              ✓ Saved {formatNaira(Number(amount))} · pay {payDate}
            </p>
          )}
        </form>
      </div>
    </section>
  );
}
