interface CommandSuggestionsProps {
    onSelect: (command: string) => void;
    visible: boolean;
}

export function CommandSuggestions({ onSelect, visible }: CommandSuggestionsProps) {
    if (!visible) return null;

    const rows = [
        ["check system", "run cleanup", "show processes"],
        ["search files ~/", "read file", "list downloads"],
        ["show tasks", "create task", "show goals"],
        ["open workspace", "check emails", "open jira"]
    ];

    return (
        <div className="mb-4 flex flex-col gap-2 transition-opacity duration-300">
            {rows.map((row, i) => (
                <div key={i} className="flex gap-2 justify-center flex-wrap">
                    {row.map(cmd => (
                        <button
                            key={cmd}
                            onClick={() => onSelect(cmd)}
                            className="px-3 py-1 rounded-full border border-[rgba(0,255,204,0.2)] bg-transparent text-[var(--nova-muted)] font-mono text-xs hover:border-[var(--nova-accent)] hover:bg-[rgba(0,255,204,0.05)] hover:text-[var(--nova-accent)] transition-all cursor-pointer"
                        >
                            {cmd}
                        </button>
                    ))}
                </div>
            ))}
        </div>
    );
}
