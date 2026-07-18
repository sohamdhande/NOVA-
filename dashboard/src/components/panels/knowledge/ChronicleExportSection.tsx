import { useState } from "react";
import { PROMPT_VERSION, CHRONICLE_EXPORT_PROMPT } from "../../../constants/chronicleExportPrompt";

export function ChronicleExportSection() {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(CHRONICLE_EXPORT_PROMPT);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (e) {
            console.error("Failed to copy", e);
        }
    };

    return (
        <div className="flex flex-col gap-2 mb-4 border-b border-[var(--nova-border)]/50 pb-4">
            <h1 className="text-xs font-mono text-[var(--nova-accent)] tracking-widest uppercase">Chronicle Export</h1>
            <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-[var(--nova-muted)] uppercase tracking-wider">
                    Prompt Version v{PROMPT_VERSION}
                </span>
                <button
                    onClick={handleCopy}
                    className="flex items-center justify-center w-8 h-8 rounded border border-[var(--nova-border)] bg-[var(--nova-surface)] hover:bg-[var(--nova-surface2)] hover:border-[var(--nova-accent)]/50 transition-colors text-[var(--nova-text)] group relative"
                    title={copied ? "Prompt Copied" : "Copy Chronicle Prompt"}
                >
                    <span className={`text-sm transition-transform duration-200 ${copied ? "text-[var(--nova-green)] scale-110" : "text-[var(--nova-muted)] group-hover:text-[var(--nova-text)]"}`}>
                        {copied ? "✓" : "⧉"}
                    </span>
                </button>
            </div>
        </div>
    );
}
