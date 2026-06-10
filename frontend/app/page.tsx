"use client";

import { useCallback, useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import ChatInterface from "@/components/ChatInterface";
import FinancialSummaryPanel from "@/components/FinancialSummary";
import UploadStatement from "@/components/UploadStatement";
import SalaryInput from "@/components/SalaryInput";
import BillsPanel from "@/components/BillsPanel";
import MobileNav, { MobileTab } from "@/components/MobileNav";
import { ToastProvider } from "@/components/Toast";
import BackendStatus from "@/components/BackendStatus";
import { getSummary, FinancialSummary } from "@/lib/api";

function PanelDivider() {
  return <div className="h-px bg-[var(--bg-border)] shrink-0" />;
}

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [mobileTab, setMobileTab] = useState<MobileTab>("chat");

  const loadSummary = useCallback(async () => {
    setLoading(true);
    try {
      setSummary(await getSummary());
    } catch {
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSummary();
  }, [refreshKey, loadSummary]);

  const refresh = () => setRefreshKey((k) => k + 1);

  const dataSections = (
    <>
      <FinancialSummaryPanel summary={summary} loading={loading} />
      <PanelDivider />
      <UploadStatement onUploaded={refresh} />
      <PanelDivider />
      <SalaryInput summary={summary} onSaved={refresh} />
    </>
  );

  return (
    <ToastProvider>
    <div className="min-h-screen bg-[var(--bg-base)] flex flex-col lg:flex-row">
      {/* Hackathon badge */}
      <div className="fixed top-3 right-3 z-50 hidden sm:block">
        <span
          className="text-[10px] font-medium tracking-wide px-2.5 py-1 rounded-md border text-[var(--brand)]"
          style={{ borderColor: "var(--brand)", background: "var(--brand-dim)" }}
        >
          Google Cloud Rapid Agent Hackathon 2026
        </span>
      </div>

      <Sidebar summary={summary} loading={loading} />

      {/* Main chat */}
      <main
        className={`flex-1 flex flex-col min-h-0 lg:h-screen ${
          mobileTab !== "chat" ? "hidden lg:flex" : "flex h-[calc(100dvh-64px)] lg:h-screen"
        }`}
      >
        <div className="lg:hidden flex items-center gap-2 px-4 py-3 border-b border-[var(--bg-border)] bg-[var(--bg-surface)] shrink-0">
          <span className="text-lg">🛡️</span>
          <div>
            <p className="text-[15px] font-bold tracking-[-0.5px] text-[var(--text-primary)]">
              BillGuard
            </p>
            <p className="label-caps">AI Finance Agent</p>
          </div>
        </div>
        <ChatInterface onDataChanged={refresh} />
      </main>

      {/* Desktop right panel */}
      <aside className="hidden lg:flex lg:flex-col lg:w-[360px] lg:shrink-0 lg:h-screen lg:sticky lg:top-0 border-l border-[var(--bg-border)] bg-[var(--bg-surface)] overflow-y-auto">
        <BackendStatus />
        {dataSections}
        <PanelDivider />
        <BillsPanel refreshKey={refreshKey} onDataChanged={refresh} />
      </aside>

      {/* Mobile: Overview tab */}
      {mobileTab === "data" && (
        <div className="lg:hidden flex flex-col w-full overflow-y-auto pb-20 min-h-[calc(100dvh-64px)] border-t border-[var(--bg-border)] bg-[var(--bg-surface)]">
          <BackendStatus />
          {dataSections}
        </div>
      )}

      {/* Mobile: Bills tab */}
      {mobileTab === "bills" && (
        <div className="lg:hidden flex flex-col w-full overflow-y-auto pb-20 min-h-[calc(100dvh-64px)] border-t border-[var(--bg-border)] bg-[var(--bg-surface)]">
          <FinancialSummaryPanel summary={summary} loading={loading} />
          <PanelDivider />
          <BillsPanel refreshKey={refreshKey} onDataChanged={refresh} />
        </div>
      )}

      <MobileNav active={mobileTab} onChange={setMobileTab} />
    </div>
    </ToastProvider>
  );
}
