"use client";

import { useState } from "react";

/**
 * The output that actually changes behaviour.
 *
 * A verdict page nobody sends is useless — the person who received the forward
 * needs something short enough to paste straight back into the group chat.
 */
export function ShareCorrection({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard API is unavailable in some embedded/insecure contexts.
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="rounded-lg border border-edge bg-bg-raised">
      <div className="flex items-center justify-between border-b border-edge px-4 py-2.5">
        <span className="font-mono text-[10px] tracking-[0.18em] text-fg-subtle">
          READY TO PASTE
        </span>
        <button
          type="button"
          onClick={copy}
          className="inline-flex items-center gap-1.5 rounded border border-edge px-2.5 py-1 text-[11px] font-medium text-fg transition hover:border-edge-strong hover:bg-bg-sunken"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="p-4">
        <div className="rounded-md border border-edge bg-bg-sunken px-4 py-3.5">
          <p className="text-[13px] leading-relaxed text-fg">{text}</p>
        </div>
        <p className="mt-2.5 text-[11px] text-fg-subtle">
          {text.length} characters · sized for a WhatsApp or Telegram reply
        </p>
      </div>
    </div>
  );
}
