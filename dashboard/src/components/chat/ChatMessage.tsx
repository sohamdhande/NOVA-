import { SystemBlock } from './blocks/SystemBlock';
import { ShellBlock } from './blocks/ShellBlock';
import { FilesBlock } from './blocks/FilesBlock';
import { TasksBlock } from './blocks/TasksBlock';
import { MissionBlock } from './blocks/MissionBlock';
import { ApprovalBlock } from './blocks/ApprovalBlock';
import { ErrorBlock } from './blocks/ErrorBlock';

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
    onApprove: () => void;
    onDeny: () => void;
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
                    <MissionBlock data={message.data} />
                )}
                {(message.block_type === 'approval' || message.requires_approval) && (
                    <ApprovalBlock
                        data={message.data}
                        risk={message.risk || 'MEDIUM'}
                        onApprove={onApprove}
                        onDeny={onDeny}
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
                        <div className="px-3 py-2 rounded bg-[#0a1a1a] border border-[rgba(0,255,204,0.15)] text-[#e2e8f0] font-mono text-sm whitespace-pre-wrap">
                            {message.content}
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
