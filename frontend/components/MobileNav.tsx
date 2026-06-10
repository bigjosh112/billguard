"use client";

import { MessageSquare, LayoutGrid, Receipt } from "lucide-react";

export type MobileTab = "chat" | "data" | "bills";

interface MobileNavProps {
  active: MobileTab;
  onChange: (tab: MobileTab) => void;
}

const tabs: { id: MobileTab; label: string; icon: typeof MessageSquare }[] = [
  { id: "chat", label: "Agent", icon: MessageSquare },
  { id: "data", label: "Overview", icon: LayoutGrid },
  { id: "bills", label: "Bills", icon: Receipt },
];

export default function MobileNav({ active, onChange }: MobileNavProps) {
  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50 flex items-stretch border-t border-[var(--bg-border)] bg-[var(--bg-surface)]">
      {tabs.map(({ id, label, icon: Icon }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className="flex-1 flex flex-col items-center justify-center gap-1 py-3 transition-colors duration-150"
            style={{ color: isActive ? "var(--brand)" : "var(--text-muted)" }}
          >
            <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
            <span className="text-[10px] font-medium tracking-wide">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
