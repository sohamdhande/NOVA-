import { useState } from 'react';

interface ApprovalProps {
    data: any;
    risk: string;
    onApprove: () => void;
    onDeny: () => void;
}

export function ApprovalBlock({ data, risk, onApprove, onDeny }: ApprovalProps) {
    const [status, setStatus] = useState<'pending' | 'approved' | 'denied'>('pending');
    const isHighRisk = risk === 'HIGH';
    const borderColor = isHighRisk ? 'border-[var(--nova-red)]' : 'border-[var(--nova-amber)]';
    const textColor = isHighRisk ? 'text-[var(--nova-red)]' : 'text-[var(--nova-amber)]';

    const handleApprove = () => {
        setStatus('approved');
        onApprove();
    };

    const handleDeny = () => {
        setStatus('denied');
        onDeny();
    };

    return (
        <div className={`bg-[#0a0a0a] border ${borderColor} rounded p-3 font-mono flex flex-col gap-3`}>
            <div className={`${textColor} text-xs border-b ${borderColor}/30 pb-2`}>
                ┌─ AUTHORIZATION REQUIRED
            </div>
            <div className={`text-xs ${textColor} font-bold`}>
                {isHighRisk ? '⚠ HIGH RISK OPERATION' : '⚠ MEDIUM RISK OPERATION'}
            </div>
            {(data?.command || data?.action || data?.path) && (
                <div className="text-[var(--nova-text)] text-xs mt-1">
                    Command: {data.command || data.action || data.path}
                </div>
            )}

            {status === 'pending' ? (
                <div className="flex gap-4 mt-2">
                    <button
                        onClick={handleApprove}
                        className="flex-1 py-1 px-3 border border-[var(--nova-green)] text-[var(--nova-green)] hover:bg-[var(--nova-green)]/10 text-xs transition-colors rounded cursor-pointer"
                    >
                        APPROVE
                    </button>
                    <button
                        onClick={handleDeny}
                        className="flex-1 py-1 px-3 border border-[var(--nova-red)] text-[var(--nova-red)] hover:bg-[var(--nova-red)]/10 text-xs transition-colors rounded cursor-pointer"
                    >
                        DENY
                    </button>
                </div>
            ) : (
                <div className={`mt-2 text-xs font-bold ${status === 'approved' ? 'text-[var(--nova-green)]' : 'text-[var(--nova-red)]'}`}>
                    {status === 'approved' ? 'Approved ✓' : 'Denied ✗'}
                </div>
            )}
        </div>
    );
}
