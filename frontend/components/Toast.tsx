"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import { Check, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "info";

export interface ToastData {
  message: string;
  type: ToastType;
  id: string;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}

function ToastItem({ toast }: { toast: ToastData }) {
  const styles = {
    success: {
      bg: "rgba(16, 185, 129, 0.1)",
      border: "rgba(16, 185, 129, 0.3)",
      icon: <Check size={14} className="text-emerald-400 shrink-0" />,
    },
    error: {
      bg: "rgba(239, 68, 68, 0.1)",
      border: "rgba(239, 68, 68, 0.3)",
      icon: <X size={14} className="text-red-400 shrink-0" />,
    },
    info: {
      bg: "var(--brand-dim)",
      border: "var(--brand)",
      icon: <Info size={14} className="text-[var(--brand)] shrink-0" />,
    },
  }[toast.type];

  return (
    <div
      className="flex items-center gap-2.5 rounded-[10px] px-4 py-2.5 text-[13px] text-[var(--text-primary)] shadow-lg animate-toast-in pointer-events-auto"
      style={{
        background: styles.bg,
        border: `1px solid ${styles.border}`,
      }}
    >
      {styles.icon}
      <span>{toast.message}</span>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastData[]>([]);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts((prev) => [...prev, { message, type, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-6 left-6 z-50 flex flex-col gap-2 pointer-events-none max-w-sm">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
