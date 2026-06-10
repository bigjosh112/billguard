"use client";

import dynamic from "next/dynamic";

const ReactMarkdown = dynamic(() => import("react-markdown"), {
  ssr: false,
  loading: () => <span className="text-[var(--text-secondary)]">…</span>,
});

interface MarkdownMessageProps {
  content: string;
}

export default function MarkdownMessage({ content }: MarkdownMessageProps) {
  return (
    <ReactMarkdown
      components={{
        strong: ({ children }) => (
          <strong className="text-[var(--brand)] font-semibold">{children}</strong>
        ),
        code: ({ children }) => (
          <code className="font-mono text-[12px] bg-[var(--bg-elevated)] px-1.5 py-0.5 rounded">
            {children}
          </code>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
