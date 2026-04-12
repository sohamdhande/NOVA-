import { SystemBlock } from './blocks/SystemBlock';
import { ShellBlock } from './blocks/ShellBlock';
import { FilesBlock } from './blocks/FilesBlock';
import { TasksBlock } from './blocks/TasksBlock';
import { MissionBlock } from './blocks/MissionBlock';
import { ApprovalBlock } from './blocks/ApprovalBlock';
import { ErrorBlock } from './blocks/ErrorBlock';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export interface NovaMessage {
    id: string;
    role: 'user' | 'nova';
    content: string;
    block_type?: string;
    data?: any;
    requires_approval?: boolean;
    risk?: string;
    success?: boolean;
    timestamp: Date;
}

export function ChatMessage({
    message,
    onApprove,
    onDeny
}: {
    message: NovaMessage;
    onApprove?: (id?: string, action?: string) => void;
    onDeny?: (id?: string) => void;
}) {

    // User messages: simple right-aligned bubble
    if (message.role === 'user') {
        return (
            <div className="flex justify-end mb-3">
                <div className="max-w-sm px-3 py-2 rounded bg-cyan-950 border border-cyan-800 text-cyan-100 font-mono text-sm">
                    {message.content}
                </div>
            </div>
        );
    }

    // N.O.V.A messages: render appropriate block
    return (
        <div className="flex justify-start mb-3">
            <div className="max-w-lg w-full">
                {/* NOVA label */}
                <span className="text-[#00ffcc] text-xs font-mono mb-1 block">N.O.V.A</span>

                {/* Pick block based on type */}
                {message.block_type === 'system' && (
                    <SystemBlock data={message.data} />
                )}
                {message.block_type === 'shell' && (
                    <ShellBlock data={message.data} />
                )}
                {message.block_type === 'files' && (
                    <FilesBlock data={message.data} />
                )}
                {message.block_type === 'tasks' && (
                    <TasksBlock data={message.data} />
                )}
                {message.block_type === 'mission' && (
                    <>
                        <MissionBlock data={message.data} />
                        {message.content && 
                         message.content.length > 20 && (
                            <div className="px-3 py-2 
                              rounded bg-[#0a1a1a] 
                              border border-[rgba(0,255,204,0.15)] 
                              text-[#e2e8f0] font-mono 
                              text-sm mt-2 prose prose-invert prose-sm max-w-none">
                                <ReactMarkdown
                                    components={{
                                        h1: ({children}) => <h1 className="text-[#00ffcc] text-base font-bold mb-2">{children}</h1>,
                                        h2: ({children}) => <h2 className="text-[#00ffcc] text-sm font-bold mb-1 mt-2">{children}</h2>,
                                        h3: ({children}) => <h3 className="text-[#00ddaa] text-sm font-semibold mb-1">{children}</h3>,
                                        strong: ({children}) => <strong className="text-[#00ffcc] font-bold">{children}</strong>,
                                        p: ({children}) => <p className="mb-2 leading-relaxed">{children}</p>,
                                        ul: ({children}) => <ul className="list-none mb-2 space-y-1">{children}</ul>,
                                        li: ({children}) => <li className="flex gap-2"><span className="text-[#00ffcc]">▸</span><span>{children}</span></li>,
                                        code: ({children}) => <code className="bg-[#001a1a] text-[#00ffcc] px-1 rounded text-xs">{children}</code>,
                                        hr: () => <hr className="border-[rgba(0,255,204,0.2)] my-2" />,
                                    }}
                                >
                                    {message.content}
                                </ReactMarkdown>
                            </div>
                        )}
                    </>
                )}
                {message.block_type === 'cleanup_approval' && (
                    <div className="rounded bg-[#0a1a1a] border border-[rgba(0,255,204,0.2)] p-4 font-mono">
                        
                        {/* Report content */}
                        <div className="text-[#e2e8f0] text-sm whitespace-pre-wrap mb-4 leading-relaxed">
                            {message.content}
                        </div>
                        
                        {/* Action buttons */}
                        {!message.data?.executed && (
                            <div className="flex gap-3 mt-3 border-t border-[rgba(0,255,204,0.1)] pt-3">
                                <button
                                    onClick={() => onApprove?.(
                                        message.id, 
                                        'ai_cleanup_execute'
                                    )}
                                    className="flex-1 py-2 px-4 rounded border border-[#00ffcc]/40 text-[#00ffcc] text-xs font-mono font-bold hover:bg-[#00ffcc]/10 transition-all">
                                    ✓ YES — EXECUTE CLEANUP
                                </button>
                                <button
                                    onClick={() => onDeny?.(
                                        message.id
                                    )}
                                    className="flex-1 py-2 px-4 rounded border border-red-500/40 text-red-400 text-xs font-mono font-bold hover:bg-red-500/10 transition-all">
                                    ✕ NO — CANCEL
                                </button>
                            </div>
                        )}
                        
                        {message.data?.executed && (
                            <div className="text-[#00ffcc] text-xs font-mono mt-2 border-t border-[rgba(0,255,204,0.1)] pt-2">
                                ✓ Cleanup executed
                            </div>
                        )}
                    </div>
                )}
                {(message.block_type === 'approval' || (message.requires_approval && message.block_type !== 'cleanup_approval')) && (
                    <ApprovalBlock
                        data={message.data}
                        risk={message.risk || 'MEDIUM'}
                        onApprove={() => onApprove?.(message.id)}
                        onDeny={() => onDeny?.(message.id)}
                    />
                )}
                {(message.block_type === 'error' || message.success === false) && message.block_type !== 'approval' && (
                    <ErrorBlock
                        data={message.data}
                        message={message.content}
                    />
                )}
                {(message.block_type === 'text' || message.block_type === 'navigation' || !message.block_type) &&
                    !message.requires_approval && message.success !== false && (
                        <div className="px-3 py-2 rounded bg-[#0a1a1a] border border-[rgba(0,255,204,0.15)] text-[#e2e8f0] font-mono text-sm mt-2 max-w-none">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                a: ({ href, children }) => (
                                  <a
                                    href={href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-400 underline hover:text-blue-300 break-all"
                                  >
                                    {children}
                                  </a>
                                ),
                                code: ({ inline, children }: any) => (
                                  inline
                                    ? <code className="bg-gray-800 text-green-400 px-1 rounded text-sm">{children}</code>
                                    : <pre className="bg-gray-900 text-green-400 p-3 rounded-lg overflow-x-auto text-sm my-2">
                                        <code>{children}</code>
                                      </pre>
                                ),
                                h1: ({ children }) => <h1 className="text-xl font-bold text-white mt-3 mb-1">{children}</h1>,
                                h2: ({ children }) => <h2 className="text-lg font-semibold text-white mt-3 mb-1">{children}</h2>,
                                h3: ({ children }) => <h3 className="text-base font-semibold text-gray-200 mt-2 mb-1">{children}</h3>,
                                ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2 text-gray-300">{children}</ul>,
                                ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2 text-gray-300">{children}</ol>,
                                li: ({ children }) => <li className="text-gray-300">{children}</li>,
                                p: ({ children }) => <p className="text-gray-300 my-1 leading-relaxed">{children}</p>,
                                strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                                blockquote: ({ children }) => (
                                  <blockquote className="border-l-4 border-blue-500 pl-3 my-2 text-gray-400 italic">
                                    {children}
                                  </blockquote>
                                ),
                                table: ({ children }) => (
                                  <div className="overflow-x-auto my-2">
                                    <table className="min-w-full text-sm text-gray-300 border border-gray-700 rounded">
                                      {children}
                                    </table>
                                  </div>
                                ),
                                th: ({ children }) => <th className="px-3 py-2 bg-gray-800 text-white font-semibold border border-gray-700">{children}</th>,
                                td: ({ children }) => <td className="px-3 py-2 border border-gray-700">{children}</td>,
                              }}
                            >
                              {message.content}
                            </ReactMarkdown>
                        </div>
                    )}

                {/* Timestamp */}
                <span className="text-[#4a6a6a] text-[10px] font-mono mt-1 block">
                    {message.timestamp.toLocaleTimeString()}
                </span>
            </div>
        </div>
    );
}
