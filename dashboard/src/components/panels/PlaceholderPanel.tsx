interface Props {
    title: string;
    description?: string;
    icon?: string;
}

export function PlaceholderPanel({ title, description, icon }: Props) {
    return (
        <div className="flex-1 flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-4 border border-dashed border-[var(--nova-border)] rounded-lg px-16 py-12">
                {icon && <span className="text-4xl opacity-50">{icon}</span>}
                <h2 className="text-lg font-mono font-semibold tracking-[0.2em] text-[var(--nova-accent)] uppercase">{title}</h2>
                {description && (
                    <p className="text-xs font-mono text-[var(--nova-muted)] text-center max-w-xs">{description}</p>
                )}
                <span className="text-[9px] font-mono tracking-[0.3em] uppercase text-[var(--nova-amber)] mt-2">COMING NEXT</span>
            </div>
        </div>
    );
}
