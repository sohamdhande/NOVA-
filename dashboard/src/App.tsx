
import { useState, useEffect, useCallback } from 'react';
import { api, getToken, clearToken } from './api';
import { Login } from './components/Login';
import { Setup } from './components/Setup';
import { StatusBar } from './components/StatusBar';
import { Banner } from './components/Banner';
import { MissionStatus } from './components/MissionStatus';

type View = 'LOADING' | 'SETUP' | 'LOGIN' | 'DASHBOARD';

function App() {
  const [view, setView] = useState<View>('LOADING');
  const [statusData, setStatusData] = useState<any>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.getStatus();
      setStatusData(data);

      if (data.auth_setup_required) {
        setView('SETUP');
        return;
      }

      const token = getToken();
      if (!token) {
        setView('LOGIN');
        return;
      }

      if (data.authenticated) {
        setView('DASHBOARD');
      } else {
        clearToken();
        setView('LOGIN');
      }

    } catch (err) {
      console.error(err);
      setView('LOGIN');
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (view !== 'DASHBOARD') return;
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [view, fetchStatus]);

  const handleRestartSuccess = () => {
    // Immediate refresh
    fetchStatus();
    // And maybe schedule another one in 2s in case thread takes time to start
    setTimeout(fetchStatus, 2000);
  };

  if (view === 'LOADING') return <div className="auth-screen">INITIALIZING NOVA...</div>;
  if (view === 'SETUP') return <Setup onSetupSuccess={() => setView('LOGIN')} />;
  if (view === 'LOGIN') return <Login onLoginSuccess={fetchStatus} />;

  return (
    <div className="container">
      <StatusBar
        mode={statusData?.mode || "UNKNOWN"}
        daemonRunning={statusData?.daemon_running}
        expiresAt={localStorage.getItem("nova_session_expiry")}
      />

      <Banner
        daemonRunning={statusData?.daemon_running}
        onRestart={handleRestartSuccess}
      />

      <MissionStatus />

      <div className="dashboard-grid">
        <div className="panel placeholder-box">MORNING BRIEFING</div>
        <div className="panel placeholder-box">TASK ORCHESTRATION</div>
        <div className="panel placeholder-box">FINANCIAL TRACKING</div>
      </div>
    </div>
  );
}

export default App;
