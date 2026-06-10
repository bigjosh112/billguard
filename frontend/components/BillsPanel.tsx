"use client";

import { useEffect, useState } from "react";
import { Check, ChevronDown, Plus, Trash2 } from "lucide-react";
import {
  addBill,
  deleteBill,
  getBills,
  markBillPaid,
  Bill,
  BillInput,
  formatNaira,
} from "@/lib/api";
import { categoryIcon, daysUntilDue, dueBadgeStyle } from "@/lib/utils";
import { useToast } from "@/components/Toast";

interface BillsPanelProps {
  refreshKey?: number;
  onDataChanged?: () => void;
}

const CATEGORIES = [
  "rent",
  "loan_savings",
  "utilities",
  "transport",
  "food",
  "subscriptions",
  "other",
];

function isPaidThisMonth(paidAt?: string): boolean {
  if (!paidAt) return true;
  const d = new Date(paidAt);
  const now = new Date();
  return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
}

function formatPaidDate(paidAt?: string): string {
  if (!paidAt) return "Paid recently";
  const d = new Date(paidAt);
  return `Paid ${d.toLocaleDateString("en-NG", { month: "short", day: "numeric" })}`;
}

export default function BillsPanel({ refreshKey, onDataChanged }: BillsPanelProps) {
  const { showToast } = useToast();
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [showPaid, setShowPaid] = useState(false);
  const [confirmingPaid, setConfirmingPaid] = useState<string | null>(null);
  const [form, setForm] = useState<BillInput>({
    name: "",
    amount: 0,
    due_date: "",
    category: "utilities",
  });
  const [saving, setSaving] = useState(false);

  const loadBills = async () => {
    try {
      const data = await getBills(true);
      setBills(data.bills);
    } catch {
      setBills([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBills();
  }, [refreshKey]);

  const activeBills = bills.filter((b) => !b.paid);
  const paidBills = bills.filter((b) => b.paid && isPaidThisMonth(b.paid_at));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.amount || !form.due_date) return;

    setSaving(true);
    try {
      await addBill(form);
      setForm({ name: "", amount: 0, due_date: "", category: "utilities" });
      setExpanded(false);
      await loadBills();
      onDataChanged?.();
      showToast(`${form.name} added`, "success");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    await deleteBill(id);
    setBills((prev) => prev.filter((b) => b._id !== id));
    onDataChanged?.();
    showToast(`${name} removed`, "info");
  };

  const handleMarkPaid = async (billId: string, billName: string) => {
    const previous = bills;
    setBills((prev) =>
      prev.map((b) => (b._id === billId ? { ...b, paid: true, paid_at: new Date().toISOString() } : b))
    );
    setConfirmingPaid(null);

    try {
      await markBillPaid(billId);
      showToast(`✓ ${billName} marked as paid`, "success");
      onDataChanged?.();
    } catch {
      setBills(previous);
      showToast("Failed to update bill", "error");
    }
  };

  const renderBillCard = (
    bill: Bill,
    options: { dimmed?: boolean; actions?: boolean; index?: number } = {}
  ) => {
    const { dimmed = false, actions = true, index = 0 } = options;
    const days = daysUntilDue(bill.due_date);
    const badge = dueBadgeStyle(days);

    return (
      <li
        key={bill._id}
        className={`group relative flex items-center gap-3 p-3 rounded-xl border border-[var(--bg-border)] bg-[var(--bg-base)] transition-all duration-150 hover:bg-[var(--bg-elevated)] ${
          dimmed
            ? "opacity-50"
            : "hover:-translate-y-px animate-fade-in-up opacity-0"
        }`}
        style={!dimmed ? { animationDelay: `${index * 40}ms`, animationFillMode: "forwards" } : undefined}
      >
        <span className="text-lg shrink-0">{categoryIcon(bill.category)}</span>
        <div className="flex-1 min-w-0">
          <p
            className={`text-[14px] font-medium text-[var(--text-primary)] truncate ${
              dimmed ? "line-through" : ""
            }`}
          >
            {bill.name}
          </p>
          <p className="font-mono text-[12px] text-[var(--text-muted)]">
            {formatNaira(bill.amount)}
            {dimmed ? ` · ${formatPaidDate(bill.paid_at)}` : ` · ${bill.due_date}`}
          </p>
        </div>

        {!dimmed && (
          <span
            className="shrink-0 text-[11px] font-mono font-semibold px-2 py-1 rounded-md"
            style={{ background: badge.bg, color: badge.color }}
          >
            {badge.label}
          </span>
        )}

        {actions && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
            <button
              type="button"
              onClick={() => setConfirmingPaid(bill._id)}
              className="p-1.5 rounded-lg text-[var(--text-muted)] hover:bg-emerald-500/10 hover:text-emerald-400 transition-all"
              title="Mark as paid"
            >
              <Check size={14} />
            </button>
            <button
              type="button"
              onClick={() => handleDelete(bill._id, bill.name)}
              className="p-1.5 rounded-lg text-[var(--text-muted)] hover:bg-red-500/10 hover:text-red-400 transition-all"
              title="Delete"
            >
              <Trash2 size={14} />
            </button>
          </div>
        )}

        {confirmingPaid === bill._id && (
          <div className="absolute inset-0 bg-[var(--bg-surface)]/95 rounded-xl flex items-center justify-between px-4 border border-emerald-500/30 z-10">
            <span className="text-xs text-[var(--text-secondary)] truncate pr-2">
              Mark {bill.name} as paid?
            </span>
            <div className="flex gap-2 shrink-0">
              <button
                type="button"
                onClick={() => handleMarkPaid(bill._id, bill.name)}
                className="text-xs px-3 py-1.5 bg-emerald-500 text-[#080B14] rounded-lg font-medium hover:bg-emerald-400 transition-colors"
              >
                Paid ✓
              </button>
              <button
                type="button"
                onClick={() => setConfirmingPaid(null)}
                className="text-xs px-3 py-1.5 bg-[var(--bg-elevated)] text-[var(--text-muted)] rounded-lg hover:text-[var(--text-primary)] transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </li>
    );
  };

  return (
    <section>
      <div className="section-header flex items-center justify-between">
        <p className="label-caps">Upcoming Bills</p>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-[11px] text-[var(--brand)] hover:text-[var(--brand-hover)] transition-colors"
        >
          <Plus size={12} />
          Add Bill
        </button>
      </div>

      <div className="p-5">
        {expanded && (
          <form
            onSubmit={handleSubmit}
            className="space-y-2 mb-4 pb-4 border-b border-[var(--bg-border)] animate-fade-in-up"
          >
            <input
              type="text"
              placeholder="Bill name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="input-dark w-full"
            />
            <div className="grid grid-cols-2 gap-2">
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] text-[13px]">
                  ₦
                </span>
                <input
                  type="number"
                  placeholder="Amount"
                  value={form.amount || ""}
                  onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
                  className="input-dark w-full pl-7 font-mono"
                />
              </div>
              <input
                type="date"
                value={form.due_date}
                onChange={(e) => setForm({ ...form, due_date: e.target.value })}
                className="input-dark w-full font-mono"
              />
            </div>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="input-dark w-full"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c} style={{ background: "#0F1524" }}>
                  {c.replace(/_/g, " ")}
                </option>
              ))}
            </select>
            <button
              type="submit"
              disabled={saving}
              className="w-full py-2.5 rounded-lg text-[13px] font-semibold transition-all duration-200 disabled:opacity-50"
              style={{ background: "var(--brand)", color: "#080B14" }}
            >
              {saving ? "Adding…" : "Add Bill"}
            </button>
          </form>
        )}

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-[10px] bg-[var(--bg-elevated)] animate-pulse" />
            ))}
          </div>
        ) : activeBills.length === 0 ? (
          <p className="text-[13px] text-[var(--text-muted)] text-center py-4">
            No bills due. Tap + Add Bill to get started.
          </p>
        ) : (
          <ul className="space-y-2 max-h-80 overflow-y-auto">
            {activeBills.map((bill, i) => renderBillCard(bill, { index: i }))}
          </ul>
        )}

        {paidBills.length > 0 && (
          <>
            <button
              type="button"
              onClick={() => setShowPaid(!showPaid)}
              className="w-full text-left text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] py-2 flex items-center gap-1 transition-colors mt-2"
            >
              <ChevronDown
                size={12}
                className={`transition-transform duration-200 ${showPaid ? "rotate-180" : ""}`}
              />
              {paidBills.length} paid this month
            </button>

            {showPaid && (
              <ul className="space-y-1 mt-1">
                {paidBills.map((bill) => renderBillCard(bill, { dimmed: true, actions: false }))}
              </ul>
            )}
          </>
        )}
      </div>
    </section>
  );
}
