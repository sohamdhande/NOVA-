import { useState, useEffect } from "react";

interface ApprovalEvent {
    id: number;
    source: string;
    type: string;
    payload: {
        command: string;
        reason: string;
    };
    priority: number;
    timestamp: string;
    status: string;
}

import { api } from "../../api";

export function ApprovalQueue() {
    const [approvals, setApprovals] = useState<ApprovalEvent[]>([]);

    const fetchApprovals = async () => {
        try {
            const data = await api.getApprovals();
            setApprovals(data);
        } catch (e) {
            console.error("Failed to fetch approvals:", e);
        }
    };

    useEffect(() => {
        fetchApprovals();
        const interval = setInterval(fetchApprovals, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleApprove = async (id: number) => {
        try {
            await api.approveAction(id);
            fetchApprovals();
        } catch (e) {
            console.error(e);
        }
    };

    const handleDeny = async (id: number) => {
        try {
            await api.denyAction(id);
            fetchApprovals();
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="w-full mt-4 max-w-[420px] px-4 self-center">
            {approvals.length === 0 ? (
                <div className="text-[10px] text-white/30 font-mono italic text-center">No pending approvals</div>
            ) : (
                <div className="space-y-3">
                    {approvals.map(a => {
                        const isHigh = a.priority >= 8;
                        const badgeColor = isHigh ? "bg-critical/20 text-critical" : "bg-warning/20 text-warning";
                        const riskLevel = isHigh ? "HIGH" : "MEDIUM";

                        return (
                            <div key={a.id} className="bg-white/[0.03] border border-white/[0.06] p-3 font-mono">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="text-[11px] font-medium text-white/90 uppercase tracking-widest">{a.payload.command}</div>
                                    <div className={`text-[8px] px-1.5 py-0.5 rounded-sm ${badgeColor}`}>
                                        {riskLevel} RISK
                                    </div>
                                </div>
                                <div className="text-xs text-white/50 mb-3">{a.payload.reason}</div>
                                <div className="text-[9px] text-white/30 mb-3">{new Date(a.timestamp).toLocaleString()}</div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => handleApprove(a.id)}
                                        className="flex-1 bg-white/10 hover:bg-success/20 hover:text-success text-white/70 py-1.5 text-[10px] uppercase tracking-widest transition-colors rounded-sm"
                                    >
                                        Approve
                                    </button>
                                    <button
                                        onClick={() => handleDeny(a.id)}
                                        className="flex-1 bg-white/10 hover:bg-critical/20 hover:text-critical text-white/70 py-1.5 text-[10px] uppercase tracking-widest transition-colors rounded-sm"
                                    >
                                        Deny
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
