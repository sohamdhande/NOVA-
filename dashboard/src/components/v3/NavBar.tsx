import { motion } from 'framer-motion';

export type NavSection = 'OVERVIEW' | 'TASKS' | 'FINANCE' | 'INTELLIGENCE' | 'SYSTEM';

interface NavBarProps {
    activeSection: NavSection;
    onNavigate: (section: NavSection) => void;
}

const sections: NavSection[] = ['OVERVIEW', 'TASKS', 'FINANCE', 'INTELLIGENCE', 'SYSTEM'];

export const NavBar = ({ activeSection, onNavigate }: NavBarProps) => {
    return (
        <nav className="flex items-center gap-12 border-b border-white/[0.04] pb-px">
            {sections.map((section) => (
                <button
                    key={section}
                    onClick={() => onNavigate(section)}
                    className="relative py-4 text-xs tracking-[0.2em] font-light transition-colors hover:text-white group"
                >
                    <span className={`relative z-10 transition-colors duration-300 ${activeSection === section ? 'text-white' : 'text-white/40'}`}>
                        {section}
                    </span>

                    {/* Animated Underline */}
                    {activeSection === section && (
                        <motion.div
                            layoutId="nav-underline"
                            className="absolute bottom-0 left-0 right-0 h-[2px] bg-accent/80 shadow-[0_0_8px_rgba(31,111,235,0.6)]"
                            transition={{ type: "spring", stiffness: 350, damping: 30 }}
                        />
                    )}

                    {/* Hover Glow */}
                    <div className="absolute inset-0 bg-white/[0.02] opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-md -z-10 scale-90 group-hover:scale-100" />
                </button>
            ))}
        </nav>
    );
};
