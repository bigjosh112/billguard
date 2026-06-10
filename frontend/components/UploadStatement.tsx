"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, CloudUpload, FileText } from "lucide-react";
import { uploadStatement } from "@/lib/api";
import { useToast } from "@/components/Toast";

const UPLOAD_STAGES = [
  { pct: 8, label: "Reading your bank statement...", duration: 400 },
  { pct: 22, label: "Detecting bank format...", duration: 500 },
  { pct: 38, label: "Parsing transactions...", duration: 600 },
  { pct: 55, label: "Categorising spending...", duration: 700 },
  { pct: 70, label: "Detecting subscriptions...", duration: 600 },
  { pct: 82, label: "Storing in MongoDB...", duration: 500 },
  { pct: 91, label: "Building your financial picture...", duration: 400 },
  { pct: 97, label: "Almost done...", duration: 300 },
];

interface UploadStatementProps {
  onUploaded: () => void;
}

export default function UploadStatement({ onUploaded }: UploadStatementProps) {
  const { showToast } = useToast();
  const [dragging, setDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [transactionCount, setTransactionCount] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const timeoutsRef = useRef<number[]>([]);

  const clearTimeouts = useCallback(() => {
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
  }, []);

  const scheduleTimeout = useCallback((fn: () => void, ms: number) => {
    const id = window.setTimeout(fn, ms);
    timeoutsRef.current.push(id);
    return id;
  }, []);

  useEffect(() => () => clearTimeouts(), [clearTimeouts]);

  const runProgressStages = useCallback(() => {
    let delay = 0;
    UPLOAD_STAGES.forEach((stage) => {
      scheduleTimeout(() => {
        setUploadProgress(stage.pct);
        setUploadStage(stage.label);
      }, delay);
      delay += stage.duration;
    });
  }, [scheduleTimeout]);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith(".csv")) {
        setError("Please upload a CSV bank statement.");
        return;
      }

      clearTimeouts();
      setSelectedFile(file);
      setIsUploading(true);
      setUploadProgress(0);
      setUploadStage("");
      setUploadSuccess(false);
      setError(null);

      runProgressStages();

      try {
        const result = await uploadStatement(file);
        setUploadProgress(100);
        setUploadStage("Done!");

        scheduleTimeout(() => {
          setIsUploading(false);
          setUploadSuccess(true);
          setTransactionCount(result.transactions_imported);
          showToast(
            `${result.transactions_imported} transactions imported ✓`,
            "success"
          );

          scheduleTimeout(() => {
            setUploadSuccess(false);
            setSelectedFile(null);
            setUploadProgress(0);
            setUploadStage("");
            onUploaded();
          }, 3000);
        }, 800);
      } catch (err) {
        clearTimeouts();
        setIsUploading(false);
        setUploadProgress(0);
        setUploadStage("");
        setSelectedFile(null);
        setError(err instanceof Error ? err.message : "Upload failed");
      }
    },
    [onUploaded, runProgressStages, clearTimeouts, scheduleTimeout, showToast]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <section>
      <div className="section-header">
        <p className="label-caps">Upload Statement</p>
      </div>
      <div className="p-5">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className="rounded-xl p-8 text-center transition-all duration-200"
          style={{
            background: uploadSuccess
              ? "rgba(16, 185, 129, 0.05)"
              : dragging
                ? "var(--brand-dim)"
                : "var(--bg-base)",
            border: uploadSuccess
              ? "2px solid var(--accent-emerald)"
              : dragging
                ? "2px dashed var(--brand)"
                : "2px dashed var(--bg-border)",
          }}
        >
          {uploadSuccess ? (
            <div className="py-6 text-center">
              <div
                className="mx-auto mb-3 flex h-14 w-14 animate-bounce-once items-center justify-center rounded-full border border-[var(--accent-emerald)] bg-emerald-500/10"
              >
                <Check size={28} className="text-[var(--accent-emerald)]" />
              </div>
              <p className="mb-1 font-mono text-lg font-bold text-[var(--text-primary)]">
                {transactionCount} transactions imported
              </p>
              <p className="text-xs text-[var(--text-muted)]">
                MongoDB updated · Financial summary refreshed
              </p>
            </div>
          ) : isUploading ? (
            <div>
              {selectedFile && (
                <div className="mb-4 flex items-center gap-2 rounded-lg border border-[var(--bg-border)] bg-[var(--bg-elevated)] px-3 py-2">
                  <FileText size={14} className="shrink-0 text-[var(--brand)]" />
                  <span className="truncate font-mono text-xs text-[var(--text-secondary)]">
                    {selectedFile.name}
                  </span>
                  <span className="ml-auto shrink-0 text-xs text-[var(--text-muted)]">
                    {(selectedFile.size / 1024).toFixed(0)}KB
                  </span>
                </div>
              )}

              <div className="mb-4 relative mx-auto w-12">
                <div className="relative z-10 mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-[var(--brand)] bg-[var(--brand-dim)]">
                  <FileText size={22} className="text-[var(--brand)]" />
                </div>
                <div className="absolute inset-0 rounded-xl border-2 border-[var(--brand)] opacity-30 animate-ping" />
              </div>

              <p className="mb-3 h-5 text-sm text-[var(--text-secondary)] transition-all duration-300">
                {uploadStage}
              </p>

              <div className="mb-2 h-1.5 w-full rounded-full bg-[var(--bg-elevated)]">
                <div
                  className="h-1.5 rounded-full bg-gradient-to-r from-[var(--brand)] to-emerald-400"
                  style={{
                    width: `${uploadProgress}%`,
                    transition: "width 0.4s ease-out",
                  }}
                />
              </div>

              <p className="font-mono text-xs text-[var(--text-muted)]">
                {uploadProgress}%
              </p>
            </div>
          ) : (
            <>
              <CloudUpload size={24} className="mx-auto mb-3 text-[var(--text-muted)]" />
              <p className="mb-1 text-[14px] text-[var(--text-secondary)]">
                Drop your bank statement
              </p>
              <p className="text-[12px] text-[var(--text-muted)]">
                GTBank · Access · Zenith · UBA
              </p>
            </>
          )}
        </div>

        <label className="mt-3 flex justify-center">
          <span className="inline-flex cursor-pointer items-center rounded-lg border border-[var(--bg-border)] px-4 py-2 text-[13px] text-[var(--text-secondary)] transition-all duration-200 hover:border-[var(--brand)] hover:text-[var(--text-primary)]">
            {isUploading ? "Uploading…" : "Choose CSV file"}
            <input
              type="file"
              accept=".csv"
              className="hidden"
              disabled={isUploading}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
              }}
            />
          </span>
        </label>

        {error && (
          <p className="mt-2 text-center text-[12px] text-[var(--accent-red)]">{error}</p>
        )}
      </div>
    </section>
  );
}
