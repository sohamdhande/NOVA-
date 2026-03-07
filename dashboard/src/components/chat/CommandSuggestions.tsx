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
        <div className="transition-opacity duration-300">
            <div className="flex flex-wrap gap-2 p-3 border-b border-[rgba(0,255,204,0.08)] justify-center">
                {rows.flat().map(cmd => (
                    <button
                        key={cmd}
                        onClick={() => onSelect(cmd)}
                        className="px-3 py-1 rounded-full font-mono text-xs border border-[rgba(0,255,204,0.3)] text-[#00ffcc] bg-transparent hover:bg-[rgba(0,255,204,0.08)] hover:border-[rgba(0,255,204,0.6)] hover:shadow-[0_0_8px_rgba(0,255,204,0.2)] transition-all duration-200 cursor-pointer whitespace-nowrap"
                    >
                        {cmd}
                    </button>
                ))}
            </div>
        </div>
    );
}
