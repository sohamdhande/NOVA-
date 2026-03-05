
// src/components/MissionStatus.tsx
import React, { useEffect, useState } from 'react';
import { api } from '../api';

interface MissionSummary {
    active_tasks_count: number;
    overdue_count: number;
    deadlines_48h_count: number;
    expenses_missing_today: boolean;
    missing_expense_days_count: number;
    daemon_running: boolean;
    daemon_last_error?: string | null;
}

export const MissionStatus: React.FC = () => {
    const [summary, setSummary] = useState<MissionSummary | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchSummary = async () => {
        try {
            const data = await api.getSummary();
            setSummary(data);
        } catch (e) {
            console.error("Failed to fetch summary", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSummary();
        const interval = setInterval(fetchSummary, 30000); // 30s refresh
        return () => clearInterval(interval);
    }, []);

    if (loading || !summary) return <div className="panel" style={{ height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>LOADING MISSION STATUS...</div>;

    return (
        <div className="panel">
            <div className="mission-header">MISSION STATUS</div>
            <div className="mission-grid">
                {/* Tasks */}
                <div className="stat-box">
                    <div className="stat-label">ACTIVE TASKS</div>
                    <div className="stat-value">{summary.active_tasks_count}</div>
                </div>

                <div className="stat-box">
                    <div className="stat-label">OVERDUE</div>
                    <div className={`stat-value ${summary.overdue_count > 0 ? 'red' : 'green'}`}>
                        {summary.overdue_count}
                    </div>
                </div>

                <div className="stat-box">
                    <div className="stat-label">48H DEADLINES</div>
                    <div className={`stat-value ${summary.deadlines_48h_count > 0 ? 'amber' : 'neutral'}`}>
                        {summary.deadlines_48h_count}
                    </div>
                </div>

                {/* Expenses */}
                <div className="stat-box">
                    <div className="stat-label">EXPENSE LOG</div>
                    <div className={`stat-value ${summary.expenses_missing_today ? 'red' : 'green'}`}>
                        {summary.expenses_missing_today ? "MISSING" : "LOGGED"}
                    </div>
                </div>

                {/* Last Error (Only show if present) */}
                {summary.daemon_last_error && (
                    <div className="stat-box full-width" style={{ borderColor: 'var(--accent-red)' }}>
                        <div className="stat-label red">DAEMON ERROR</div>
                        <div className="stat-value small-text red">
                            {summary.daemon_last_error.split('\n').pop() || "Unknown Error"}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
