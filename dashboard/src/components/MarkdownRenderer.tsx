import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
    content: string;
    className?: string;
}

export function MarkdownRenderer({ content, className = "" }: Props) {
    if (!content) return null;

    return (
        <div className={`markdown-body space-y-3 text-sm leading-relaxed ${className}`}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    a: ({ href, children }) => (
                        <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[var(--nova-accent)] underline hover:brightness-125 break-all font-medium"
                        >
                            {children}
                        </a>
                    ),
                    code: ({ inline, children }: any) => (
                        inline
                            ? <code className="bg-[var(--nova-surface2)] text-[var(--nova-accent)] px-1.5 py-0.5 rounded text-[0.88em] font-mono border border-[var(--nova-border)]">{children}</code>
                            : <pre className="bg-[var(--nova-surface2)] text-[var(--nova-accent)] p-4 rounded-lg overflow-x-auto text-[13px] my-3 font-mono border border-[var(--nova-border)] leading-normal">
                                <code>{children}</code>
                              </pre>
                    ),
                    h1: ({ children }) => <h1 className="text-xl font-bold text-[var(--nova-accent)] mt-4 mb-2 tracking-wide font-mono">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg font-bold text-[var(--nova-accent)] mt-3.5 mb-2 font-mono">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-base font-bold text-[var(--nova-text)] mt-3 mb-1.5 font-mono">{children}</h3>,
                    ul: ({ children }) => <ul className="list-disc list-inside space-y-2 my-2.5 text-[var(--nova-text)] pl-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal list-inside space-y-2 my-2.5 text-[var(--nova-text)] pl-1">{children}</ol>,
                    li: ({ children }) => <li className="text-[var(--nova-text)] leading-relaxed">{children}</li>,
                    p: ({ children }) => <p className="text-[var(--nova-text)] my-2.5 leading-relaxed">{children}</p>,
                    strong: ({ children }) => <strong className="text-[var(--nova-accent)] font-bold">{children}</strong>,
                    em: ({ children }) => <em className="text-[var(--nova-amber)] not-italic font-semibold">{children}</em>,
                    blockquote: ({ children }) => (
                        <blockquote className="border-l-2 border-[var(--nova-accent)] pl-3.5 my-3 text-[var(--nova-muted)] italic">
                            {children}
                        </blockquote>
                    ),
                    table: ({ children }) => (
                        <div className="overflow-x-auto my-3">
                            <table className="min-w-full text-[13px] text-[var(--nova-text)] border border-[var(--nova-border)] rounded">
                                {children}
                            </table>
                        </div>
                    ),
                    th: ({ children }) => <th className="px-3.5 py-2.5 bg-[var(--nova-surface2)] text-[var(--nova-accent)] font-bold border border-[var(--nova-border)] text-left">{children}</th>,
                    td: ({ children }) => <td className="px-3.5 py-2.5 border border-[var(--nova-border)]">{children}</td>,
                    hr: () => <hr className="border-[var(--nova-border)] my-4" />
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
