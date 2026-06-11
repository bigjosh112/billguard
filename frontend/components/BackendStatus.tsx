"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

type Status = "checking" | "ok" | "wrong" | "offline";

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.location.hostname === "localhost") return;

    (async () => {
      try {
        const res = await fetch("/backend/health");
        const data = await res.json().catch(() => ({}));
        if (data.service === "BillGuard" && data.database === "connected") {
          setStatus("ok");
          return;
        }
        if (data.service === "BillGuard") {
          setStatus("wrong");
          setDetail("MongoDB not connected — check MONGODB_URI on Railway.");
          return;
        }
        setStatus("wrong");
        setDetail(
          "Backend misconfigured — check Railway service (rootDir=backend, startCommand=uvicorn)."
        );
      } catch {
        setStatus("offline");
        setDetail("Backend unreachable — server may be waking up. Wait 30s and refresh.");
      }
    })();
  }, []);

  if (status === "checking" || status === "ok") return null;

  return (
    <div
      className={`mx-3 mt-2 rounded-lg border px-3 py-2 text-xs flex gap-2 items-start ${
        status === "offline"
          ? "border-amber-500/40 bg-amber-500/10 text-amber-200"
          : "border-red-500/40 bg-red-500/10 text-red-200"
      }`}
    >
      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
      <div>
        <p className="font-medium">
          {status === "offline" ? "Backend offline" : "Backend misconfigured"}
        </p>
        <p className="opacity-90 mt-0.5">{detail}</p>
      </div>
    </div>
  );
}

export function BackendOkBadge() {
  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400">
      <CheckCircle2 className="w-3 h-3" /> API connected
    </span>
  );
}
