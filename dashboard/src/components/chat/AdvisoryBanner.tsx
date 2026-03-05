import { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';

interface Advisory {
    id: string;
    type: 'critical' | 'warning' | 'info';
    message: string;
    action: string | null;
    priority: number;
}

interface AdvisoryBannerProps {
    onActionClick: (command: string) => void;
}

export function AdvisoryBanner({ onActionClick }: AdvisoryBannerProps) {
    const [advisory, setAdvisory] = useState<Advisory | null>(null);
    const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
    const { get } = useApi();

    useEffect(() => {
        let timeoutId: number;
        let isActive = true;

        const fetchAdvisories = async () => {
            try {
                const res = await get<{ advisories: Advisory[] }>('/api/advisories');
                if (!isActive) return;

                // Find highest priority non-dismissed
                const activeAdvisory = res.advisories.find(a => !dismissedIds.has(a.id));
                setAdvisory(activeAdvisory || null);

                // Auto-dismiss after 30 seconds if one is shown
                if (activeAdvisory) {
                    clearTimeout(timeoutId);
                    timeoutId = window.setTimeout(() => {
                        if (isActive) {
                            handleDismiss(activeAdvisory.id);
                        }
                    }, 30000);
                }
            } catch (e) {
                console.error("Failed to fetch advisories", e);
            }
        };

        fetchAdvisories();
        const intervalId = setInterval(fetchAdvisories, 60000);

        return () => {
            isActive = false;
            clearInterval(intervalId);
            clearTimeout(timeoutId);
        };
    }, [get, dismissedIds]);

    const handleDismiss = (id: string) => {
        setDismissedIds(prev => {
            const next = new Set(prev);
            next.add(id);
            return next;
        });
        setAdvisory(null);
    };

    if (!advisory) return null;

    const colors = {
        critical: 'border-[var(--nova-red)] text-[var(--nova-red)]',
        warning: 'border-[var(--nova-amber)] text-[var(--nova-amber)]',
        info: 'border-[var(--nova-accent)] text-[var(--nova-accent)]'
    };

    const bgColors = {
        critical: 'bg-[var(--nova-red)]',
        warning: 'bg-[var(--nova-amber)]',
        info: 'bg-[var(--nova-accent)]'
    };

    return (
        <div className={`mb-4 bg-[#0a0a0a] border ${colors[advisory.type]} rounded flex flex-col font-mono relative overflow-hidden transition-all duration-300 slide-in-top`}>
            <div className={`absolute left-0 top-0 bottom-0 w-1 ${bgColors[advisory.type]}`} />

            <div className="p-3 pl-4 flex flex-col gap-2">
                <div className={`text-xs border-b ${colors[advisory.type]} pb-2 opacity-80 flex justify-between`}>
                    <span>┌─ ADVISORY</span>
                </div>

                <div className="text-[var(--nova-text)] text-xs flex gap-2">
                    <span className={colors[advisory.type]}>⚠</span>
                    <span className="flex-1">{advisory.message}</span>
                </div>

                <div className="flex justify-end gap-3 mt-1">
                    {advisory.action && (
                        <button
                            onClick={() => {
                                onActionClick(advisory.action!);
                                handleDismiss(advisory.id);
                            }}
                            className="text-[10px] text-[var(--nova-accent)] hover:underline cursor-pointer tracking-wider"
                        >
                            [{advisory.action.toUpperCase()}]
                        </button>
                    )}
                    <button
                        onClick={() => handleDismiss(advisory.id)}
                        className="text-[10px] text-[var(--nova-muted)] hover:text-[var(--nova-text)] transition-colors cursor-pointer tracking-wider"
                    >
                        [DISMISS]
                    </button>
                </div>
            </div>
        </div>
    );
}
