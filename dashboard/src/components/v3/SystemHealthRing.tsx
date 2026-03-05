import { motion } from 'framer-motion';

interface SystemHealthRingProps {
    health: number;
    zone?: 'stable' | 'controlled' | 'elevated' | 'critical';
}

const zoneColors = {
    stable: '#FFFFFF',
    controlled: '#00F0FF',
    elevated: '#F4C430',
    critical: '#FF4D4D',
};

export const SystemHealthRing = ({ health, zone = 'stable' }: SystemHealthRingProps) => {
    const color = zoneColors[zone];

    // Complex Ring Configuration
    // Outer: 130px radius
    // Middle: 110px radius
    // Inner: 90px radius

    return (
        <div className="relative w-[300px] h-[300px] flex items-center justify-center">
            {/* Critical Pulse */}
            {zone === 'critical' && (
                <motion.div
                    className="absolute inset-0 rounded-full border-2 border-critical opacity-20"
                    animate={{ scale: [1, 1.1, 1], opacity: [0.2, 0, 0.2] }}
                    transition={{ duration: 2, repeat: Infinity }}
                />
            )}

            {/* Ring 1: Outer Segments (Clockwise) */}
            <motion.svg
                className="absolute inset-0 w-full h-full"
                animate={{ rotate: 360 }}
                transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
            >
                <circle cx="150" cy="150" r="140" stroke={color} strokeWidth="1" fill="transparent" strokeDasharray="20 40" opacity="0.3" />
                <circle cx="150" cy="150" r="135" stroke={color} strokeWidth="4" fill="transparent" strokeDasharray="100 200" opacity="0.1" />
            </motion.svg>

            {/* Ring 2: Middle Dashes (Counter-Clockwise) */}
            <motion.svg
                className="absolute inset-0 w-full h-full"
                animate={{ rotate: -360 }}
                transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
            >
                <circle cx="150" cy="150" r="110" stroke={color} strokeWidth="1" fill="transparent" strokeDasharray="4 8" opacity="0.5" />
                <circle cx="150" cy="150" r="110" stroke={color} strokeWidth="8" fill="transparent" strokeDasharray="2 350" opacity="0.8" />
            </motion.svg>

            {/* Ring 3: Inner Static & Progress */}
            <svg className="absolute inset-0 w-full h-full -rotate-90">
                {/* Track */}
                <circle cx="150" cy="150" r="90" stroke={color} strokeWidth="2" fill="transparent" opacity="0.1" />
                {/* Value */}
                <motion.circle
                    cx="150" cy="150" r="90"
                    stroke={color} strokeWidth="3" fill="transparent"
                    strokeDasharray={2 * Math.PI * 90}
                    strokeDashoffset={2 * Math.PI * 90 * (1 - health / 100)}
                    initial={{ strokeDashoffset: 2 * Math.PI * 90 }}
                    animate={{ strokeDashoffset: 2 * Math.PI * 90 * (1 - health / 100) }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    strokeLinecap="round"
                    style={{ filter: `drop-shadow(0 0 4px ${color})` }}
                />
            </svg>

            {/* Decorative Arcs */}
            <svg className="absolute inset-0 w-full h-full">
                <path d="M 50 150 A 100 100 0 0 1 250 150" stroke={color} strokeWidth="1" fill="transparent" opacity="0.1" />
                <path d="M 150 290 L 150 300" stroke={color} strokeWidth="2" opacity="0.5" />
                <path d="M 150 10 L 150 0" stroke={color} strokeWidth="2" opacity="0.5" />
            </svg>

            {/* Center Content */}
            <div className="absolute flex flex-col items-center justify-center">
                <motion.div
                    className="text-6xl font-bold tracking-tighter"
                    style={{ color, textShadow: `0 0 20px ${color}80` }}
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                >
                    {Math.round(health)}
                </motion.div>
                <div className="text-xs tracking-[0.3em] font-light opacity-60" style={{ color }}>
                    SYSTEM
                </div>
                <div className="text-[10px] bg-white/10 px-2 py-0.5 rounded mt-2 font-mono text-white/50">
                    {zone.toUpperCase()}
                </div>
            </div>
        </div>
    );
};
