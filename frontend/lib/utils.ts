export function daysUntilDue(dueDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dueDate + "T00:00:00");
  return Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

export function categoryIcon(category: string): string {
  const map: Record<string, string> = {
    rent: "🏠",
    loan: "💳",
    loan_savings: "💳",
    utilities: "⚡",
    transport: "🚗",
    food: "🍔",
    healthcare: "💊",
    education: "📚",
    shopping: "🛍️",
    subscriptions: "📱",
    subscription: "📱",
    other: "📋",
  };
  return map[category] || "📋";
}

export function dueBadgeStyle(days: number): {
  bg: string;
  color: string;
  label: string;
} {
  if (days <= 3) {
    return {
      bg: "rgba(239, 68, 68, 0.12)",
      color: "var(--accent-red)",
      label: days <= 0 ? "⚠ Due" : `⚠ ${days}d`,
    };
  }
  if (days <= 7) {
    return {
      bg: "rgba(245, 158, 11, 0.12)",
      color: "var(--accent-amber)",
      label: `${days}d`,
    };
  }
  return {
    bg: "var(--bg-elevated)",
    color: "var(--text-muted)",
    label: `${days}d`,
  };
}
