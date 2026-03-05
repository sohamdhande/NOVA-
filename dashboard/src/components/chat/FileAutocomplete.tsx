import { useState, useEffect, useCallback } from 'react';
import { useApi } from '../../hooks/useApi';

interface Suggestion {
    path: string;
    is_dir: boolean;
    name: string;
}

interface FileAutocompleteProps {
    query: string;
    onSelect: (path: string) => void;
    visible: boolean;
}

export function FileAutocomplete({ query, onSelect, visible }: FileAutocompleteProps) {
    const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const { get } = useApi();

    const fetchSuggestions = useCallback(async (q: string) => {
        try {
            // Extract the path portion (last word)
            const parts = q.split(' ');
            const lastPart = parts[parts.length - 1];
            if (!lastPart || (!lastPart.includes('~/') && !lastPart.startsWith('/'))) {
                setSuggestions([]);
                return;
            }

            const res = await get<{ suggestions: Suggestion[] }>(`/api/files/autocomplete?q=${encodeURIComponent(lastPart)}`);
            setSuggestions(res.suggestions || []);
            setSelectedIndex(0);
        } catch {
            setSuggestions([]);
        }
    }, [get]);

    // Debounce logic
    useEffect(() => {
        if (!visible) {
            setSuggestions([]);
            return;
        }

        const timeoutId = setTimeout(() => {
            fetchSuggestions(query);
        }, 300);

        return () => clearTimeout(timeoutId);
    }, [query, visible, fetchSuggestions]);

    // Keyboard navigation
    useEffect(() => {
        if (!visible || suggestions.length === 0) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex(prev => (prev + 1) % suggestions.length);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex(prev => (prev - 1 + suggestions.length) % suggestions.length);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (suggestions[selectedIndex]) {
                    onSelect(suggestions[selectedIndex].path);
                }
            } else if (e.key === 'Escape') {
                // We handle closing via HQPanel effectively by parent state, 
                // but can safely blur or hide in a real scenario
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [visible, suggestions, selectedIndex, onSelect]);

    if (!visible || suggestions.length === 0) return null;

    return (
        <div className="absolute bottom-full left-0 w-full mb-2 bg-[#0a0a0a] border border-[var(--nova-accent)] rounded overflow-hidden shadow-lg z-50">
            <div className="max-h-48 overflow-y-auto">
                {suggestions.map((s, idx) => (
                    <div
                        key={s.path}
                        className={`px-3 py-2 flex items-center gap-2 cursor-pointer font-mono text-xs text-[var(--nova-text)]
              ${idx === selectedIndex ? 'bg-[var(--nova-accent)]/20' : 'hover:bg-[var(--nova-accent)]/5'}
            `}
                        onClick={() => onSelect(s.path)}
                        onMouseEnter={() => setSelectedIndex(idx)}
                    >
                        <span className="opacity-70">{s.is_dir ? '📁' : '📄'}</span>
                        <span className="truncate">{s.path}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
