import { useState, useEffect, useCallback } from 'react';
import { authenticatedFetch, API_BASE, getToken } from '../../api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/* ── Types ── */
type Decision = { decision: string; reasoning: string; contradicts_prior: boolean; confidence: string };
type Assumption = { assumption: string; why: string; could_break_if: string };
type Uncertainty = { question: string; why_it_matters: string; blocker: boolean };
type NextAction = { action: string; depends_on: string | null; owner: string | null; timeline: string | null };

type DistillResult = {
  project: string;
  decided: Decision[];
  assumed: Assumption[];
  uncertain: Uncertainty[];
  next_actions: NextAction[];
  contradictions: string[];
  context?: { fact: string; relevance: string }[];
};

type ProjectSummary = {
  project: string;
  entry_count: number;
  source_types: string[];
  tags: string[];
  recent_entries: { id: string; title: string; summary: string; source_type: string; timestamp: string; tags: string[] }[];
};

/* ── Component ── */
export function DistillPanel() {
  const [project, setProject] = useState('');
  const [projects, setProjects] = useState<string[]>([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [showNewProject, setShowNewProject] = useState(false);
  const [thread, setThread] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamChunks, setStreamChunks] = useState('');
  const [result, setResult] = useState<DistillResult | null>(null);
  const [savingMemory, setSavingMemory] = useState(false);
  const [memorySaved, setMemorySaved] = useState(false);
  const [projectSummary, setProjectSummary] = useState<ProjectSummary | null>(null);
  const [showAllMemories, setShowAllMemories] = useState(false);
  
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportMarkdown, setExportMarkdown] = useState('');
  const [copied, setCopied] = useState(false);

  // Chat states
  const [activeTab, setActiveTab] = useState<'distill' | 'chat'>('distill');
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<{role: string, content: string}[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const isTooLarge = thread.length > 400_000;

  /* ── Export Handler ── */
  const handleExport = async () => {
    if (!project) return;
    setExportLoading(true);
    setShowExportModal(true);
    setExportMarkdown('');
    setCopied(false);
    
    try {
      const res = await authenticatedFetch(`/api/distill/export/${encodeURIComponent(project)}`);
      if (!res.ok) throw new Error('Failed to export project');
      const data = await res.json();
      setExportMarkdown(data.markdown || 'No context found.');
    } catch (err: any) {
      setExportMarkdown(`Error exporting project: ${err.message}`);
    } finally {
      setExportLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (!exportMarkdown) return;
    navigator.clipboard.writeText(exportMarkdown).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      // Fallback
      const textArea = document.createElement("textarea");
      textArea.value = exportMarkdown;
      document.body.appendChild(textArea);
      textArea.select();
      try { document.execCommand('copy'); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch (err) { }
      document.body.removeChild(textArea);
    });
  };

  const downloadMarkdown = () => {
    if (!exportMarkdown) return;
    const blob = new Blob([exportMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const date = new Date().toISOString().split('T')[0];
    a.download = `${project}-context-${date}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  /* ── Fetch projects ── */
  const fetchProjects = useCallback(async () => {
    try {
      const res = await authenticatedFetch('/api/memory/projects');
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  /* ── Fetch project summary ── */
  useEffect(() => {
    if (!project) { setProjectSummary(null); return; }
    (async () => {
      try {
        const res = await authenticatedFetch(`/api/memory/project/${encodeURIComponent(project)}`);
        if (res.ok) setProjectSummary(await res.json());
      } catch { setProjectSummary(null); }
    })();
  }, [project]);

  /* ── Create new project ── */
  const handleCreateProject = () => {
    const name = newProjectName.trim().toLowerCase().replace(/\s+/g, '-');
    if (!name) return;
    if (!projects.includes(name)) setProjects(prev => [...prev, name].sort());
    setProject(name);
    setNewProjectName('');
    setShowNewProject(false);
  };

  /* ── Chat Handler ── */
  const handleChat = async () => {
    if (!chatMessage.trim() || !project) return;
    
    const userMsg = { role: 'user', content: chatMessage };
    setChatHistory(prev => [...prev, userMsg]);
    setChatMessage('');
    setChatLoading(true);

    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/api/distill/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ project, message: userMsg.content, history: chatHistory })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response stream');

      const decoder = new TextDecoder();
      let buffer = '';
      
      // Add empty assistant message to stream into
      setChatHistory(prev => [...prev, { role: 'assistant', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6).trim();
          if (payload === '[DONE]') continue;

          try {
            const evt = JSON.parse(payload);
            if (evt.type === 'chunk') {
              setChatHistory(prev => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.content += evt.content;
                updated[updated.length - 1] = last;
                return updated;
              });
            } else if (evt.type === 'error') {
               setChatHistory(prev => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.content += `\n[Error: ${evt.detail}]`;
                updated[updated.length - 1] = last;
                return updated;
              });
            }
          } catch { /* skip */ }
        }
      }
    } catch (err: any) {
       setChatHistory(prev => [...prev, { role: 'assistant', content: `[Error: ${err.message}]` }]);
    } finally {
      setChatLoading(false);
    }
  };

  /* ── Distill with SSE ── */
  const handleDistill = async () => {
    if (!thread.trim() || !project || isTooLarge) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setStreamChunks('');
    setMemorySaved(false);

    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/api/distill`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ project, thread })
      });

      if (!response.ok) {
        const err = await response.json().catch(() => null);
        throw new Error(err?.detail || `API Error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response stream');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6).trim();
          if (payload === '[DONE]') continue;

          try {
            const evt = JSON.parse(payload);
            if (evt.type === 'chunk') {
              setStreamChunks(prev => prev + evt.content);
            } else if (evt.type === 'complete') {
              setResult(evt.result);
            } else if (evt.type === 'error') {
              setError(evt.detail);
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (err: any) {
      setError(err.message || 'Unexpected error');
    } finally {
      setLoading(false);
    }
  };

  /* ── Save to memory ── */
  const handleSaveToMemory = async () => {
    if (!result) return;
    setSavingMemory(true);
    try {
      const now = new Date().toISOString().slice(0, 10);
      const tags = ['distillation', ...new Set([
        ...(result.decided?.map(() => 'decision') || []),
        ...(result.assumed?.map(() => 'assumption') || []),
        ...(result.uncertain?.filter(u => u.blocker).map(() => 'blocker') || []),
        ...(result.context?.map(() => 'context') || []),
      ])];

      const res = await authenticatedFetch('/api/memory/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project,
          source_type: 'distillation',
          title: `Distillation from ${now}`,
          summary: JSON.stringify(result),
          tags: [...new Set(tags)]
        })
      });
      if (!res.ok) {
        throw new Error('Failed to save');
      }
      
      const data = await res.json();
      if (data.result?.status === 'duplicate') {
        alert('Memory already exists in this project (Duplicate detected).');
      } else {
        setMemorySaved(true);
      }
      fetchProjects();
      // Refresh project summary
      const sumRes = await authenticatedFetch(`/api/memory/project/${encodeURIComponent(project)}`);
      if (sumRes.ok) setProjectSummary(await sumRes.json());
    } catch (err: any) {
      alert('Failed to save: ' + err.message);
    } finally {
      setSavingMemory(false);
    }
  };

  /* ── Confidence badge ── */
  const ConfBadge = ({ level }: { level: string }) => {
    const colors: Record<string, string> = {
      high: 'rgba(16,185,129,0.2)', medium: 'rgba(245,158,11,0.2)', low: 'rgba(239,68,68,0.2)'
    };
    const textColors: Record<string, string> = {
      high: 'var(--nova-green)', medium: 'var(--nova-amber)', low: 'var(--nova-red)'
    };
    return (
      <span style={{ background: colors[level] || colors.medium, color: textColors[level] || textColors.medium, padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>
        {level}
      </span>
    );
  };

  /* ── Skeleton ── */
  const Skeleton = () => (
    <div className="animate-pulse space-y-6">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="space-y-2">
          <div className="h-4 bg-[rgba(255,255,255,0.08)] rounded w-1/3" />
          <div className="h-3 bg-[rgba(255,255,255,0.04)] rounded w-4/5" />
          <div className="h-3 bg-[rgba(255,255,255,0.04)] rounded w-3/5" />
        </div>
      ))}
    </div>
  );

  const sectionStyle = "mb-6";
  const headerStyle = "text-xs font-bold uppercase tracking-[0.2em] mb-3 pb-2 border-b border-[var(--nova-border)] flex items-center gap-2";

  return (
    <div className="h-full p-4 overflow-y-auto">
      <div className={`max-w-[1600px] mx-auto grid grid-cols-1 ${activeTab === 'chat' ? 'lg:grid-cols-[1fr_300px]' : 'lg:grid-cols-[300px_1fr_280px]'} gap-4 h-full min-h-0`}>

        {/* ═══ LEFT COLUMN ═══ */}
        {activeTab === 'distill' && (
          <div className="flex flex-col gap-3 min-h-0">
            <h2 className="text-lg font-bold tracking-[0.15em] text-white uppercase">💎 Distillation</h2>

            {/* Project selector */}
          <div className="space-y-2">
            <div className="flex justify-between items-end">
              <label className="text-[10px] uppercase tracking-[0.2em] text-[var(--nova-muted)] font-bold">Project</label>
              {project && (
                <button 
                  onClick={handleExport}
                  className="text-[10px] uppercase tracking-wider text-[var(--nova-accent)] hover:underline flex items-center gap-1"
                >
                  <span>📄 Export</span>
                </button>
              )}
            </div>
            <div 
              className="relative w-full outline-none" 
              tabIndex={0} 
              onBlur={(e) => {
                if (!e.currentTarget.contains(e.relatedTarget)) {
                  setIsDropdownOpen(false);
                }
              }}
            >
              <div 
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="w-full bg-[rgba(0,255,204,0.03)] border border-[var(--nova-accent)]/30 rounded-md px-3 py-2 text-sm text-[var(--nova-accent)] cursor-pointer flex justify-between items-center hover:bg-[rgba(0,255,204,0.08)] hover:border-[var(--nova-accent)]/80 transition-all group shadow-[0_0_15px_rgba(0,255,204,0.05)] hover:shadow-[0_0_20px_rgba(0,255,204,0.15)] relative overflow-hidden"
              >
                {/* Cyberpunk scanning line effect */}
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[var(--nova-accent)] to-transparent opacity-0 group-hover:opacity-100 group-hover:animate-scan"></div>
                
                <div className="flex items-center gap-3">
                  <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold tracking-widest transition-colors flex items-center gap-1 ${project ? 'bg-[var(--nova-accent)]/20 text-[var(--nova-accent)] group-hover:bg-[var(--nova-accent)]/40' : 'bg-[var(--nova-muted)]/20 text-[var(--nova-muted)] group-hover:bg-[var(--nova-muted)]/40'}`}>
                    {project ? <><span className="w-1.5 h-1.5 rounded-full bg-[var(--nova-accent)] animate-pulse"></span> ACTV</> : <><span className="w-1.5 h-1.5 rounded-full bg-[var(--nova-muted)]"></span> IDLE</>}
                  </span>
                  <span className={`font-mono tracking-wider font-bold ${project ? 'text-[var(--nova-text)] drop-shadow-[0_0_8px_rgba(0,255,204,0.3)]' : 'text-[var(--nova-muted)]'}`}>
                    {project || "SELECT_DATASET_"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-[var(--nova-accent)] opacity-50 font-mono hidden sm:inline-block">[{projects.length} nodes]</span>
                  <span className={`transition-transform duration-300 font-mono text-[10px] text-[var(--nova-accent)] ${isDropdownOpen ? 'rotate-180' : ''}`}>▼</span>
                </div>
              </div>

              {isDropdownOpen && (
                <div className="absolute top-full left-0 w-full mt-2 bg-[#0a1111]/95 backdrop-blur-xl border border-[var(--nova-accent)]/40 rounded-md shadow-[0_10px_30px_rgba(0,0,0,0.8),0_0_20px_rgba(0,255,204,0.1)] z-50 overflow-hidden animate-dropdown">
                  <div className="p-2 border-b border-[var(--nova-accent)]/20 bg-gradient-to-r from-[rgba(0,255,204,0.05)] to-transparent">
                     <div className="text-[9px] uppercase tracking-widest text-[var(--nova-accent)] opacity-80 mb-1 flex justify-between items-center px-1">
                        <span>Available Nodes</span>
                        <span className="animate-pulse">●</span>
                     </div>
                  </div>
                  <div className="max-h-60 overflow-y-auto custom-scrollbar">
                    {projects.length === 0 ? (
                      <div className="px-3 py-6 text-xs text-[var(--nova-muted)] italic font-mono text-center flex flex-col items-center gap-2">
                        <span className="text-xl opacity-50">∅</span>
                        No active nodes found
                      </div>
                    ) : (
                      <div className="py-1">
                        {projects.map(p => (
                          <div 
                            key={p} 
                            onClick={() => { setProject(p); setIsDropdownOpen(false); }}
                            className={`px-3 py-2 text-sm cursor-pointer font-mono tracking-wide transition-all border-l-2 mx-1 rounded-r-sm group relative overflow-hidden ${project === p ? 'bg-[var(--nova-accent)]/10 text-[var(--nova-accent)] border-[var(--nova-accent)] shadow-[inset_0_0_10px_rgba(0,255,204,0.05)]' : 'border-transparent text-[var(--nova-text)] hover:bg-[rgba(255,255,255,0.05)] hover:border-[rgba(255,255,255,0.3)]'}`}
                          >
                            {/* Hover highlight effect */}
                            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-r from-[var(--nova-accent)]/0 to-[var(--nova-accent)]/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            
                            <div className="flex items-center justify-between relative z-10">
                              <span className="group-hover:translate-x-1 transition-transform">{p}</span>
                              {project === p ? (
                                <span className="text-[10px] animate-pulse bg-[var(--nova-accent)] text-black px-1.5 py-0.5 rounded font-bold">ACTV</span>
                              ) : (
                                <span className="text-[9px] opacity-0 group-hover:opacity-50 transition-opacity text-[var(--nova-muted)]">SELECT</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {!showNewProject ? (
              <button onClick={() => setShowNewProject(true)} className="text-[var(--nova-accent)] text-xs hover:underline">+ New Project</button>
            ) : (
              <div className="flex gap-2">
                <input
                  value={newProjectName}
                  onChange={e => setNewProjectName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleCreateProject()}
                  placeholder="project-name"
                  className="flex-1 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded px-2 py-1 text-sm text-[var(--nova-text)] focus:outline-none focus:border-[var(--nova-accent)]"
                  autoFocus
                />
                <button onClick={handleCreateProject} className="text-xs bg-[var(--nova-accent)] text-black px-3 py-1 rounded font-bold">Add</button>
                <button onClick={() => setShowNewProject(false)} className="text-xs text-[var(--nova-muted)]">✕</button>
              </div>
            )}
          </div>

          {/* Thread input */}
          <textarea
            className="flex-1 min-h-[400px] w-full bg-[rgba(255,255,255,0.02)] border border-[var(--nova-border)] rounded p-3 text-xs font-mono text-[var(--nova-text)] focus:border-[var(--nova-accent)] focus:outline-none resize-none"
            placeholder="Paste raw chat thread here…"
            value={thread}
            onChange={e => setThread(e.target.value)}
          />

          {isTooLarge && (
            <div className="text-xs text-[var(--nova-red)] font-bold">⚠ Thread too large (~{Math.round(thread.length / 4).toLocaleString()} tokens). Max ~100k.</div>
          )}

          {project && (
            <p className="text-[10px] text-[var(--nova-muted)]">
              NOVA will extract decisions, assumptions, uncertainties, and next actions for <span className="text-[var(--nova-accent)]">{project}</span>.
            </p>
          )}

          <button
            onClick={handleDistill}
            disabled={!thread.trim() || !project || isTooLarge || loading}
            className="bg-[var(--nova-accent)] text-black font-bold py-2.5 px-4 rounded uppercase tracking-wider text-sm hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed transition-all shrink-0"
          >
            {loading ? '⏳ Distilling…' : '💎 Distill'}
          </button>
        </div>
        )}

        {/* ═══ MIDDLE COLUMN ═══ */}
        <div className="flex flex-col min-h-0">
          
          {/* Tabs */}
          <div className="flex gap-4 mb-2 px-2">
            <button 
              onClick={() => setActiveTab('distill')}
              className={`text-xs font-bold uppercase tracking-wider pb-1 border-b-2 transition-colors ${activeTab === 'distill' ? 'border-[var(--nova-accent)] text-white' : 'border-transparent text-[var(--nova-muted)] hover:text-white'}`}
            >
              Distill Output
            </button>
            {project && (
              <button 
                onClick={() => setActiveTab('chat')}
                className={`text-xs font-bold uppercase tracking-wider pb-1 border-b-2 transition-colors ${activeTab === 'chat' ? 'border-[var(--nova-accent)] text-white' : 'border-transparent text-[var(--nova-muted)] hover:text-white'}`}
              >
                Project Chat
              </button>
            )}
          </div>

          <div className="flex-1 bg-[rgba(0,0,0,0.25)] border border-[var(--nova-border)] rounded p-5 overflow-y-auto relative flex flex-col">

            {activeTab === 'distill' && (
              <>
                {/* Empty state */}
                {!result && !loading && !error && !streamChunks && (
                  <div className="absolute inset-0 flex items-center justify-center text-[var(--nova-muted)] text-sm font-mono text-center px-8">
                    Distilled output will stream here.
                  </div>
                )}

                {/* Error */}
                {error && (
                  <div className="bg-[rgba(239,68,68,0.08)] border border-[var(--nova-red)] text-[var(--nova-red)] p-4 rounded text-sm mb-4">
                    <span className="font-bold block mb-1">DISTILLATION FAILED</span>{error}
                  </div>
                )}

                {/* Streaming raw chunks or fallback text */}
                {!result && (
                  <>
                    {streamChunks ? (
                      <pre className="text-xs text-[var(--nova-text)] whitespace-pre-wrap font-mono opacity-80">{streamChunks}</pre>
                    ) : loading ? (
                      <Skeleton />
                    ) : null}
                  </>
                )}

                {/* ── Structured Result ── */}
                {result && !loading && (
                  <div className="space-y-1">
                    {/* Context & Facts */}
                    {result.context && result.context.length > 0 && (
                      <div className={sectionStyle}>
                        <h3 className={headerStyle} style={{ color: '#a78bfa' }}>ℹ Context & Facts</h3>
                        <div className="space-y-3">
                          {result.context.map((c, i) => (
                            <div key={i} className="bg-[rgba(167,139,250,0.05)] border border-[rgba(167,139,250,0.15)] rounded p-3">
                              <p className="text-sm text-[var(--nova-text)]">{c.fact}</p>
                              <p className="text-xs text-[var(--nova-muted)] mt-1">Relevance: {c.relevance}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Decisions */}
                    {result.decided?.length > 0 && (
                      <div className={sectionStyle}>
                        <h3 className={headerStyle} style={{ color: 'var(--nova-green)' }}>✓ Decisions</h3>
                        <div className="space-y-3">
                          {result.decided.map((d, i) => (
                            <div key={i} className="bg-[rgba(16,185,129,0.05)] border border-[rgba(16,185,129,0.15)] rounded p-3">
                              <div className="flex items-start justify-between gap-2 mb-1">
                                <p className="text-sm text-[var(--nova-text)] font-medium">{d.decision}</p>
                                <ConfBadge level={d.confidence} />
                              </div>
                              <p className="text-xs text-[var(--nova-muted)] mt-1">{d.reasoning}</p>
                              {d.contradicts_prior && <p className="text-xs text-[var(--nova-red)] mt-1 font-bold">⚡ Contradicts prior decision</p>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Assumptions */}
                    {result.assumed?.length > 0 && (
                      <div className={sectionStyle}>
                        <h3 className={headerStyle} style={{ color: '#60a5fa' }}>⚠ Assumptions</h3>
                        <div className="space-y-3">
                          {result.assumed.map((a, i) => (
                            <div key={i} className="bg-[rgba(96,165,250,0.05)] border border-[rgba(96,165,250,0.15)] rounded p-3">
                              <p className="text-sm text-[var(--nova-text)]">{a.assumption}</p>
                              <p className="text-xs text-[var(--nova-muted)] mt-1">Why: {a.why}</p>
                              <p className="text-xs text-[var(--nova-amber)] mt-1">Breaks if: {a.could_break_if}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Uncertainties */}
                    {result.uncertain?.length > 0 && (
                      <div className={sectionStyle}>
                        <h3 className={headerStyle} style={{ color: 'var(--nova-amber)' }}>❓ Uncertainties</h3>
                        <div className="space-y-3">
                          {result.uncertain.map((u, i) => (
                            <div key={i} className={`rounded p-3 border ${u.blocker ? 'bg-[rgba(239,68,68,0.06)] border-[rgba(239,68,68,0.2)]' : 'bg-[rgba(245,158,11,0.05)] border-[rgba(245,158,11,0.15)]'}`}>
                              <div className="flex items-start gap-2">
                                {u.blocker && <span className="text-[10px] bg-[rgba(239,68,68,0.2)] text-[var(--nova-red)] px-2 py-0.5 rounded font-bold uppercase shrink-0">Blocker</span>}
                                <p className="text-sm text-[var(--nova-text)]">{u.question}</p>
                              </div>
                              <p className="text-xs text-[var(--nova-muted)] mt-1">{u.why_it_matters}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Next Actions */}
                    {result.next_actions?.length > 0 && (
                      <div className={sectionStyle}>
                        <h3 className={headerStyle} style={{ color: 'var(--nova-accent)' }}>→ Next Actions</h3>
                        <div className="space-y-2">
                          {result.next_actions.map((a, i) => (
                            <div key={i} className="bg-[rgba(0,255,204,0.03)] border border-[var(--nova-border)] rounded p-3">
                              <p className="text-sm text-[var(--nova-text)]">{a.action}</p>
                              <div className="flex flex-wrap gap-3 mt-1 text-[10px] text-[var(--nova-muted)]">
                                {a.depends_on && <span>Depends: {a.depends_on}</span>}
                                {a.owner && <span>Owner: {a.owner}</span>}
                                {a.timeline && <span>Timeline: {a.timeline}</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Contradictions */}
                    {result.contradictions?.length > 0 && (
                      <div className={sectionStyle}>
                        <h3 className={headerStyle} style={{ color: 'var(--nova-red)' }}>⚡ Contradictions</h3>
                        <div className="space-y-2">
                          {result.contradictions.map((c, i) => (
                            <div key={i} className="bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.25)] rounded p-3 text-sm text-[var(--nova-red)]">{c}</div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Save button */}
                    <div className="mt-6 pt-4 border-t border-[var(--nova-border)]">
                      <button
                        onClick={handleSaveToMemory}
                        disabled={savingMemory || memorySaved}
                        className={`w-full py-2.5 px-4 rounded text-sm font-bold uppercase tracking-wider transition-all ${
                          memorySaved
                            ? 'bg-[rgba(0,255,204,0.1)] text-[var(--nova-accent)] border border-[var(--nova-accent)]'
                            : 'bg-[rgba(255,255,255,0.05)] text-white hover:bg-[rgba(255,255,255,0.1)] border border-[var(--nova-border)]'
                        }`}
                      >
                        {memorySaved ? `✓ Saved to ${project}` : savingMemory ? 'Saving…' : `Save to ${project} Memory`}
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ── Chat View ── */}
            {activeTab === 'chat' && (
              <div className="flex flex-col h-full">
                <div className="flex-1 overflow-y-auto space-y-4 pb-4">
                  {chatHistory.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-center px-8 text-[var(--nova-muted)]">
                      <div className="text-3xl mb-3 opacity-50">🤖</div>
                      <h3 className="font-bold text-white mb-2 uppercase tracking-widest text-xs">Project Manager Mode</h3>
                      <p className="text-xs">
                        Ask any question about {project}. I have full access to all extracted decisions, assumptions, and next actions.
                      </p>
                    </div>
                  )}
                  {chatHistory.map((msg, i) => {
                    let thinkingContent = '';
                    let finalContent = msg.content;
                    let isThinking = false;
                    
                    if (msg.role === 'assistant' && msg.content.includes('<think>')) {
                      isThinking = true;
                      const parts = msg.content.split('</think>');
                      if (parts.length > 1) {
                        thinkingContent = parts[0].replace('<think>', '').trim();
                        finalContent = parts[1].trim();
                        isThinking = false;
                      } else {
                        thinkingContent = msg.content.replace('<think>', '').trim();
                        finalContent = '';
                      }
                    }

                    return (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] min-w-0 rounded p-3 text-sm ${
                          msg.role === 'user' 
                            ? 'bg-[var(--nova-accent)] text-black font-medium' 
                            : 'bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] text-[var(--nova-text)]'
                        }`}>
                          {msg.role === 'user' ? (
                            msg.content
                          ) : (
                            <div className="flex flex-col gap-3">
                              {thinkingContent && (
                                <details className="group border border-[rgba(0,255,204,0.15)] bg-[rgba(0,255,204,0.02)] rounded p-2 text-xs" open={isThinking}>
                                  <summary className="cursor-pointer font-bold uppercase tracking-wider text-[10px] text-[var(--nova-accent)] flex items-center gap-2 outline-none select-none">
                                    <span className="group-open:rotate-90 transition-transform">▶</span>
                                    {isThinking ? (
                                      <span className="flex items-center gap-1.5">
                                        Thinking Process <span className="flex gap-0.5"><span className="animate-bounce">.</span><span className="animate-bounce delay-75">.</span><span className="animate-bounce delay-150">.</span></span>
                                      </span>
                                    ) : 'View Reasoning'}
                                  </summary>
                                  <div className="mt-2 text-[var(--nova-muted)] whitespace-pre-wrap font-mono opacity-80 pl-4 border-l-2 border-[var(--nova-accent)]">
                                    {thinkingContent}
                                  </div>
                                </details>
                              )}
                              {finalContent && (
                                <div className="markdown-body">
                                  <ReactMarkdown 
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                      table: ({node, ...props}) => (
                                        <div className="overflow-x-auto w-full custom-scrollbar">
                                          <table {...props} />
                                        </div>
                                      )
                                    }}
                                  >
                                    {finalContent}
                                  </ReactMarkdown>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  {chatLoading && (
                    <div className="flex justify-start">
                      <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded p-3 text-[var(--nova-muted)] text-xs animate-pulse">
                        Thinking...
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="mt-auto pt-3 border-t border-[rgba(255,255,255,0.05)] flex gap-2">
                  <input
                    type="text"
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleChat()}
                    placeholder={`Ask about ${project}...`}
                    className="flex-1 bg-[rgba(255,255,255,0.02)] border border-[var(--nova-border)] rounded px-3 py-2 text-sm text-[var(--nova-text)] focus:border-[var(--nova-accent)] focus:outline-none"
                  />
                  <button
                    onClick={handleChat}
                    disabled={chatLoading || !chatMessage.trim()}
                    className="bg-[var(--nova-accent)] text-black px-4 py-2 rounded font-bold uppercase tracking-wider text-xs hover:brightness-110 disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              </div>
            )}

          </div>
        </div>

        {/* ═══ RIGHT COLUMN ═══ */}
        <div className="flex flex-col gap-3 min-h-0 overflow-y-auto">
          {project ? (
            <>
              <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--nova-accent)]">
                {project} Context
              </h3>

              {projectSummary ? (
                <div className="space-y-4 text-xs">
                  <div className="bg-[var(--nova-surface)] rounded p-3 border border-[var(--nova-border)]">
                    <div className="text-[var(--nova-muted)] mb-1">Entries</div>
                    <div className="text-2xl font-bold text-white">{projectSummary.entry_count}</div>
                  </div>

                  {projectSummary.source_types.length > 0 && (
                    <div>
                      <div className="text-[var(--nova-muted)] mb-1.5 font-bold uppercase tracking-wider">Sources</div>
                      <div className="flex flex-wrap gap-1">
                        {projectSummary.source_types.map(s => (
                          <span key={s} className="bg-[rgba(96,165,250,0.1)] text-[#60a5fa] px-2 py-0.5 rounded text-[10px]">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {projectSummary.tags.length > 0 && (
                    <div>
                      <div className="text-[var(--nova-muted)] mb-1.5 font-bold uppercase tracking-wider">Tags</div>
                      <div className="flex flex-wrap gap-1">
                        {projectSummary.tags.map(t => (
                          <span key={t} className="bg-[rgba(0,255,204,0.08)] text-[var(--nova-accent)] px-2 py-0.5 rounded text-[10px]">{t}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {projectSummary.recent_entries.length > 0 && (
                    <div>
                      <div className="text-[var(--nova-muted)] mb-1.5 font-bold uppercase tracking-wider">Recent</div>
                      <div className="space-y-2">
                        {projectSummary.recent_entries.slice(0, showAllMemories ? undefined : 3).map(e => (
                          <div 
                            key={e.id} 
                            onClick={() => {
                              setActiveTab('distill');
                              try {
                                const parsed = JSON.parse(e.summary);
                                setResult(parsed);
                                setStreamChunks('');
                              } catch (err) {
                                setResult(null);
                                setStreamChunks(e.summary);
                              }
                            }}
                            className="bg-[rgba(255,255,255,0.02)] border border-[var(--nova-border)] rounded p-2 cursor-pointer hover:bg-[rgba(255,255,255,0.05)] transition-colors"
                          >
                            <div className="text-[var(--nova-text)] font-medium text-[11px]">{e.title}</div>
                            <div className="text-[var(--nova-muted)] text-[10px] mt-0.5">{e.summary.slice(0, 100)}{e.summary.length > 100 ? '…' : ''}</div>
                            <div className="text-[9px] text-[var(--nova-muted)] mt-1 opacity-60">{e.timestamp?.slice(0, 10)} · {e.source_type}</div>
                          </div>
                        ))}
                      </div>
                      {projectSummary.recent_entries.length > 3 && (
                        <button
                          onClick={() => setShowAllMemories(!showAllMemories)}
                          className="text-[10px] text-[var(--nova-accent)] hover:underline mt-1"
                        >
                          {showAllMemories ? 'Show less' : `Show all ${projectSummary.recent_entries.length} entries`}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-[var(--nova-muted)]">Loading context…</p>
              )}
            </>
          ) : (
            <div className="text-xs text-[var(--nova-muted)] text-center mt-8">
              Select a project to see context.
            </div>
          )}
        </div>

      </div>

      {/* ═══ EXPORT MODAL ═══ */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4 lg:p-12 animate-in fade-in duration-200">
          <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-xl w-full max-w-5xl h-full flex flex-col shadow-2xl">
            <div className="flex justify-between items-center p-4 border-b border-[var(--nova-border)]">
              <h2 className="text-sm font-bold tracking-widest uppercase text-white">Project Context: {project}</h2>
              <button 
                onClick={() => setShowExportModal(false)}
                className="text-[var(--nova-muted)] hover:text-white"
              >✕</button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 bg-[#0a1111]">
              {exportLoading ? (
                <div className="flex h-full items-center justify-center text-[var(--nova-muted)] font-mono text-sm">
                  Generating export narrative...
                </div>
              ) : (
                <div className="markdown-body text-sm max-w-4xl mx-auto text-gray-200 bg-[var(--nova-surface)] p-8 rounded-lg shadow-2xl border border-[rgba(0,255,204,0.1)]">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                      table: ({node, ...props}) => (
                        <div className="overflow-x-auto w-full custom-scrollbar">
                          <table {...props} />
                        </div>
                      )
                    }}
                  >
                    {exportMarkdown}
                  </ReactMarkdown>
                </div>
              )}
            </div>
            
            <div className="p-4 border-t border-[var(--nova-border)] flex justify-end gap-3 bg-[var(--nova-surface2)] rounded-b-xl">
              <button
                onClick={copyToClipboard}
                disabled={exportLoading}
                className="bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] px-4 py-2 rounded text-xs font-bold uppercase tracking-wider text-white hover:bg-[rgba(255,255,255,0.1)] transition-colors flex items-center gap-2"
              >
                {copied ? '✓ Copied' : '📄 Copy to Clipboard'}
              </button>
              <button
                onClick={downloadMarkdown}
                disabled={exportLoading}
                className="bg-[var(--nova-accent)] px-4 py-2 rounded text-xs font-bold uppercase tracking-wider text-black hover:brightness-110 transition-colors flex items-center gap-2"
              >
                ⬇️ Download .md
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
