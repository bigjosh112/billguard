"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { wakeBackend } from "@/lib/fetch-with-retry";

/** Wake Render on page load so judges don't hit cold-start on first action. */
export default function WakeBackend() {
  const [message, setMessage] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.location.hostname === "localhost") {
      setReady(true);
      return;
    }

    let cancelled = false;

    (async () => {
      const ok = await wakeBackend((msg) => {
        if (!cancelled) setMessage(msg);
      });
      if (!cancelled) {
        setReady(true);
        setMessage(null);
        if (!ok) {
          setMessage("Server slow to start — try again in 30s or refresh.");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (ready && !message) return null;

  return (
    <div className="fixed inset-x-0 top-0 z-[100] flex justify-center px-4 pt-3 pointer-events-none">
      <div
        className="flex items-center gap-2 rounded-full border px-4 py-2 text-xs shadow-lg pointer-events-auto"
        style={{
          background: "var(--bg-elevated)",
          borderColor: "var(--brand)",
          color: "var(--text-primary)",
        }}
      >
        {!ready && <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--brand)]" />}
        <span>{message || "Connecting to server…"}</span>
      </div>
    </div>
  );
}
