import { motion, AnimatePresence } from 'framer-motion';
import type { Advisory } from '../../api';

interface SidePanelProps {
    isOpen: boolean;
    onClose: () => void;
    advisory: Advisory | null;
}

export const SidePanel = ({ isOpen, onClose, advisory }: SidePanelProps) => {
    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/40 z-40 backdrop-blur-sm"
                        onClick={onClose}
                    />

                    {/* Panel */}
                    <motion.div
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        className="fixed right-0 top-0 bottom-0 z-50 bg-[#0B0F14]/95 border-l border-white/10 shadow-2xl p-8 overflow-y-auto"
                        style={{ width: '35%', minWidth: '420px', maxWidth: '520px' }}
                    >
                        <div className="flex justify-between items-center mb-12">
                            <h2 className="text-sm uppercase tracking-[0.2em] text-critical/80 font-light animate-pulse">
                                System Advisory
                            </h2>
                            <button
                                onClick={onClose}
                                className="text-white/40 hover:text-white transition-colors"
                            >
                                ✕
                            </button>
                        </div>

                        {advisory ? (
                            <div className="space-y-12">
                                {/* Health Drop */}
                                <div>
                                    <div className="text-[10px] uppercase tracking-widest text-white/30 mb-2">Health Impact</div>
                                    <div className="text-5xl font-light text-critical tracking-tighter">
                                        -{advisory.drop_amount}%
                                    </div>
                                </div>

                                {/* Root Causes */}
                                <div>
                                    <div className="text-[10px] uppercase tracking-widest text-white/30 mb-4">Root Causes</div>
                                    <ul className="space-y-3">
                                        {advisory.causes.map((cause, i) => (
                                            <li key={i} className="flex items-start gap-3 text-white/70 font-light text-sm">
                                                <span className="mt-1.5 w-1 h-1 bg-critical rounded-full" />
                                                {cause}
                                            </li>
                                        ))}
                                    </ul>
                                </div>

                                {/* Recommendations */}
                                <div>
                                    <div className="text-[10px] uppercase tracking-widest text-white/30 mb-4">Corrective Actions</div>
                                    <ul className="space-y-4">
                                        {advisory.recommendations.map((rec, i) => (
                                            <li key={i} className="bg-white/[0.03] border border-white/[0.05] p-4 rounded-lg text-sm text-accent/80 font-mono">
                                                {rec}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        ) : (
                            <div className="text-white/30 text-center py-20">
                                No active advisories.
                            </div>
                        )}

                        <div className="absolute bottom-8 left-8 right-8">
                            <button
                                onClick={onClose}
                                className="w-full py-4 border border-white/10 hover:bg-white/5 text-xs uppercase tracking-widest text-white/60 transition-colors"
                            >
                                Acknowledge
                            </button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
};
