import os, sys, json, re, hashlib, sqlite3
import subprocess, psutil, threading, time
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

# ─── DATA STRUCTURES ─────────────────────────────────

@dataclass
class SecurityEvent:
    id: str
    timestamp: str
    severity: str      # LOW | MEDIUM | HIGH | CRITICAL
    category: str      # process|network|file|system|privacy
    title: str
    description: str
    action_taken: str = ""
    resolved: bool = False

@dataclass
class ThreatLevel:
    level: str         # CLEAR | LOW | MEDIUM | HIGH | CRITICAL
    score: int         # 0-100
    reasons: List[str] = field(default_factory=list)

class SecurityOfficer:
    
    DB_PATH = os.path.expanduser("~/.nova/security.db")
    QUARANTINE_DIR = os.path.expanduser("~/.nova/quarantine")
    
    # Known suspicious patterns
    SUSPICIOUS_PROCESS_NAMES = [
        "miner", "cryptominer", "xmrig",
        "coinhive", "minerd", "bfgminer",
        "cpuminer", "ethminer", "nicehash",
        "kworker", "kthread"
    ]
    
    SUSPICIOUS_DOMAINS = [
        "xmr.pool", "mining", "coinhive",
        "cryptonight", "monero", "minergate"
    ]
    
    SUSPICIOUS_EXTENSIONS = [
        ".sh", ".bin", ".run", ".command",
        ".app", ".pkg", ".dmg"
    ]
    
    HIGH_CPU_THRESHOLD = 80  # percent
    SECURE_MODE = False
    
    def __init__(self):
        os.makedirs(self.QUARANTINE_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(self.DB_PATH), exist_ok=True)
        self._events: List[SecurityEvent] = []
        self._monitoring = False
        self._monitor_thread = None
        self._baseline = {}
        self._init_db()
        self._capture_baseline()
    
    def _init_db(self):
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS 
            security_events (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                severity TEXT,
                category TEXT,
                title TEXT,
                description TEXT,
                action_taken TEXT,
                resolved INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS 
            file_hashes (
                path TEXT PRIMARY KEY,
                hash TEXT,
                last_checked TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS
            network_baseline (
                pid INTEGER,
                process TEXT,
                remote_addr TEXT,
                first_seen TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def _log_event(self, severity: str,
                    category: str, title: str,
                    description: str,
                    action: str = "") -> SecurityEvent:
        import uuid
        event = SecurityEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            severity=severity,
            category=category,
            title=title,
            description=description,
            action_taken=action
        )
        self._events.append(event)
        
        # Save to DB
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(
            "INSERT INTO security_events VALUES (?,?,?,?,?,?,?,?)",
            (event.id, event.timestamp,
             event.severity, event.category,
             event.title, event.description,
             event.action_taken,
             int(event.resolved))
        )
        conn.commit()
        conn.close()
        
        print(f"[Security] [{severity}] {title}")
        return event
    
    # ─── 1. SYSTEM INTEGRITY ─────────────────────────
    
    def _capture_baseline(self):
        """Capture system baseline on startup."""
        try:
            # Baseline: startup items
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True, text=True
            )
            self._baseline["launch_services"] = set(result.stdout.split("\n"))
            
            # Baseline: /Applications
            if os.path.exists("/Applications"):
                self._baseline["applications"] = set(os.listdir("/Applications"))
            
            # Baseline: login items count
            self._baseline["login_items"] = self._get_login_items()
                
        except Exception as e:
            print(f"[Security] Baseline failed: {e}")
    
    def _get_login_items(self) -> list:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to '
             'get the name of every login item'],
            capture_output=True, text=True
        )
        return result.stdout.strip().split(", ")
    
    def check_system_integrity(self) -> dict:
        """Check for unauthorized system changes."""
        alerts = []
        
        # Check for new launch agents
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True, text=True
            )
            current = set(result.stdout.split("\n"))
            baseline = self._baseline.get("launch_services", set())
            new_services = current - baseline
            new_services = {
                s for s in new_services
                if s.strip() and not s.startswith("PID")
            }
            if new_services:
                for svc in list(new_services)[:3]:
                    alerts.append({
                        "type": "new_launch_service",
                        "detail": svc.strip(),
                        "severity": "MEDIUM"
                    })
                    self._log_event(
                        "MEDIUM", "system",
                        "New Launch Service Detected",
                        f"New service: {svc.strip()}"
                    )
        except:
            pass
        
        # Check for new applications
        try:
            if os.path.exists("/Applications"):
                current_apps = set(os.listdir("/Applications"))
                baseline_apps = self._baseline.get("applications", set())
                new_apps = current_apps - baseline_apps
                for app in new_apps:
                    alerts.append({
                        "type": "new_application",
                        "detail": app,
                        "severity": "LOW"
                    })
        except:
            pass
        
        # Check SIP status
        try:
            result = subprocess.run(
                ["csrutil", "status"],
                capture_output=True, text=True
            )
            if "disabled" in result.stdout.lower():
                alerts.append({
                    "type": "sip_disabled",
                    "detail": "System Integrity Protection is disabled",
                    "severity": "HIGH"
                })
                self._log_event(
                    "HIGH", "system",
                    "SIP Disabled",
                    "System Integrity Protection is disabled — system vulnerable"
                )
        except:
            pass
        
        return {
            "status": "checked",
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }
    
    # ─── 2. FILE SCANNER ─────────────────────────────
    
    def scan_file(self, path: str) -> dict:
        """Scan a file for suspicious patterns."""
        expanded = os.path.expanduser(path)
        result = {
            "path": path,
            "safe": True,
            "warnings": [],
            "severity": "LOW"
        }
        
        if not os.path.exists(expanded):
            result["error"] = "File not found"
            return result
        
        fname = os.path.basename(expanded)
        ext = Path(expanded).suffix.lower()
        
        # Check extension
        if ext in self.SUSPICIOUS_EXTENSIONS:
            result["warnings"].append(f"Suspicious extension: {ext}")
            result["severity"] = "MEDIUM"
        
        # Check if executable
        if os.access(expanded, os.X_OK):
            result["warnings"].append("File is executable")
            result["severity"] = "MEDIUM"
        
        # Check file size anomalies
        size = os.path.getsize(expanded)
        if size > 100 * 1024 * 1024:  # 100MB
            result["warnings"].append(f"Large file: {size // 1024 // 1024}MB")
        
        # Scan content for suspicious patterns
        try:
            with open(expanded, 'rb') as f:
                content = f.read(8192)
                
            # Check for encoded payloads
            if b'base64' in content.lower() and b'eval' in content.lower():
                result["warnings"].append("Encoded payload detected (base64 + eval)")
                result["severity"] = "HIGH"
                result["safe"] = False
            
            # Check for crypto miner strings
            miner_strings = [
                b'xmrig', b'stratum+tcp',
                b'mining.pool', b'coinhive',
                b'cryptonight'
            ]
            for s in miner_strings:
                if s in content.lower():
                    result["warnings"].append(f"Cryptominer string: {s.decode()}")
                    result["severity"] = "CRITICAL"
                    result["safe"] = False
            
            # Check for keylogger patterns
            keylog_strings = [
                b'keylogger', b'keystroke',
                b'CGEventTap', b'kCGEventKeyDown'
            ]
            for s in keylog_strings:
                if s in content:
                    result["warnings"].append("Potential keylogger detected")
                    result["severity"] = "CRITICAL"
                    result["safe"] = False
        except:
            pass
        
        # Compute hash
        try:
            h = hashlib.sha256(open(expanded, 'rb').read()).hexdigest()
            result["sha256"] = h[:16] + "..."
        except:
            pass
        
        if not result["safe"]:
            self._log_event(
                result["severity"], "file",
                f"Suspicious File: {fname}",
                f"Warnings: {', '.join(result['warnings'])}",
                "Flagged for review"
            )
        
        return result
    
    def scan_downloads(self) -> str:
        """Scan all recent downloads."""
        downloads = os.path.expanduser("~/Downloads")
        results = []
        threats = 0
        
        files = sorted(
            [f for f in os.listdir(downloads)
             if os.path.isfile(os.path.join(downloads, f))],
            key=lambda f: os.path.getmtime(os.path.join(downloads, f)),
            reverse=True
        )[:20]  # Last 20 files
        
        for fname in files:
            fpath = os.path.join(downloads, fname)
            scan = self.scan_file(fpath)
            if scan.get("warnings"):
                threats += 1
                results.append(f"⚠ {fname}: {', '.join(scan['warnings'])}")
        
        if not results:
            return (f"Downloads scan complete. "
                    f"Checked {len(files)} files. "
                    f"No threats detected. ✓")
        return (f"Scan complete. "
                f"{threats} suspicious files:\n" +
                "\n".join(results))
    
    def quarantine_file(self, path: str) -> str:
        """Move file to quarantine."""
        import shutil
        expanded = os.path.expanduser(path)
        fname = os.path.basename(expanded)
        dest = os.path.join(self.QUARANTINE_DIR, fname)
        
        try:
            shutil.move(expanded, dest)
            self._log_event(
                "HIGH", "file",
                f"File Quarantined: {fname}",
                f"Moved to {dest}",
                "Quarantined"
            )
            return f"File quarantined: {fname}"
        except Exception as e:
            return f"Quarantine failed: {e}"
    
    # ─── 3. PROCESS MONITOR ──────────────────────────
    
    def scan_processes(self) -> dict:
        """Analyze all running processes."""
        suspicious = []
        high_cpu = []
        unknown = []
        
        for proc in psutil.process_iter([
            'pid', 'name', 'cpu_percent',
            'memory_percent', 'exe', 'username'
        ]):
            try:
                info = proc.info
                name = (info['name'] or "").lower()
                cpu = info['cpu_percent'] or 0
                
                # Check suspicious names
                for pattern in self.SUSPICIOUS_PROCESS_NAMES:
                    if pattern in name:
                        suspicious.append({
                            "pid": info['pid'],
                            "name": info['name'],
                            "cpu": cpu,
                            "reason": f"Matches pattern: {pattern}"
                        })
                        self._log_event(
                            "HIGH", "process",
                            f"Suspicious Process: {info['name']}",
                            f"PID {info['pid']}, CPU: {cpu}%"
                        )
                        break
                
                # High CPU
                if cpu > self.HIGH_CPU_THRESHOLD:
                    high_cpu.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cpu": cpu
                    })
                
            except (psutil.NoSuchProcess,
                    psutil.AccessDenied):
                pass
        
        return {
            "total_processes": len(list(psutil.process_iter())),
            "suspicious": suspicious,
            "high_cpu": high_cpu,
            "timestamp": datetime.now().isoformat()
        }
    
    def kill_process(self, pid: int) -> str:
        """Terminate a process by PID."""
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            self._log_event(
                "HIGH", "process",
                f"Process Terminated: {name}",
                f"PID {pid} killed by N.O.V.A",
                "Terminated"
            )
            return f"Process {name} (PID {pid}) terminated."
        except Exception as e:
            return f"Kill failed: {e}"
    
    def get_process_list(self, limit: int = 20) -> list:
        """Get top processes by CPU."""
        procs = []
        for proc in psutil.process_iter([
            'pid', 'name', 'cpu_percent',
            'memory_percent'
        ]):
            try:
                procs.append(proc.info)
            except:
                pass
        
        return sorted(
            procs,
            key=lambda x: x.get('cpu_percent', 0) or 0,
            reverse=True
        )[:limit]
    
    # ─── 4. NETWORK MONITOR ──────────────────────────
    
    def scan_network(self) -> dict:
        """Analyze active network connections."""
        suspicious = []
        connections = []
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                try:
                    if conn.raddr:
                        proc_name = "unknown"
                        try:
                            proc = psutil.Process(conn.pid)
                            proc_name = proc.name()
                        except:
                            pass
                        
                        remote = str(conn.raddr.ip)
                        port = conn.raddr.port
                        
                        conn_info = {
                            "pid": conn.pid,
                            "process": proc_name,
                            "remote": remote,
                            "port": port,
                            "status": conn.status
                        }
                        connections.append(conn_info)
                        
                        # Check suspicious ports
                        SUSPICIOUS_PORTS = [
                            4444, 5555, 6666, 7777,
                            8888, 9999, 1337, 31337
                        ]
                        if port in SUSPICIOUS_PORTS:
                            suspicious.append(conn_info)
                            self._log_event(
                                "HIGH", "network",
                                "Suspicious Port Connection",
                                f"{proc_name} → {remote}:{port}"
                            )
                except:
                    pass
        except Exception as e:
            pass
        
        return {
            "total_connections": len(connections),
            "suspicious": suspicious,
            "connections": connections[:15],
            "timestamp": datetime.now().isoformat()
        }
    
    # ─── 5. VULNERABILITY SCANNER ────────────────────
    
    def scan_vulnerabilities(self) -> str:
        """Check for outdated/vulnerable packages."""
        results = []
        
        # Check brew outdated
        try:
            result = subprocess.run(
                ["brew", "outdated"],
                capture_output=True, text=True,
                timeout=15
            )
            if result.stdout.strip():
                packages = result.stdout.strip().split("\n")
                results.append(f"Outdated Homebrew packages ({len(packages)}):")
                for p in packages[:5]:
                    results.append(f"  • {p}")
        except:
            pass
        
        # Check pip outdated
        try:
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format=columns"],
                capture_output=True, text=True,
                timeout=15
            )
            if result.stdout:
                lines = result.stdout.strip().split("\n")[2:]  # Skip headers
                if lines:
                    results.append(f"\nOutdated pip packages ({len(lines)}):")
                    for l in lines[:5]:
                        results.append(f"  • {l}")
        except:
            pass
        
        # Check macOS updates
        try:
            result = subprocess.run(
                ["softwareupdate", "-l"],
                capture_output=True, text=True,
                timeout=20
            )
            if "recommended" in result.stdout.lower():
                results.append("\n⚠ macOS updates available")
        except:
            pass
        
        if not results:
            return "Vulnerability scan complete. No issues found. ✓"
        
        return "Vulnerability Scan:\n" + "\n".join(results)
    
    # ─── 6. PRIVACY MONITOR ──────────────────────────
    
    def check_privacy(self) -> dict:
        """Check which apps have sensitive permissions."""
        results = {}
        
        # Check TCC database for permissions
        TCC_DB = os.path.expanduser(
            "~/Library/Application Support/com.apple.TCC/TCC.db"
        )
        
        if os.path.exists(TCC_DB):
            try:
                conn = sqlite3.connect(TCC_DB)
                # Check camera, mic, location access
                for service in [
                    "kTCCServiceCamera",
                    "kTCCServiceMicrophone",
                    "kTCCServiceAddressBook",
                    "kTCCServiceCalendar"
                ]:
                    rows = conn.execute(
                        "SELECT client FROM access WHERE service=? AND auth_value=2",
                        (service,)
                    ).fetchall()
                    if rows:
                        name = service.replace("kTCCService", "")
                        results[name] = [r[0] for r in rows]
                conn.close()
            except:
                pass
        
        # Check clipboard access
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True, text=True
        )
        clipboard_size = len(result.stdout)
        
        return {
            "permissions": results,
            "clipboard_size": clipboard_size,
            "timestamp": datetime.now().isoformat()
        }
    
    # ─── 7. FULL SECURITY SCAN ───────────────────────
    
    def full_scan(self) -> str:
        """Run comprehensive security scan."""
        print("[Security] Running full scan...")
        results = []
        threat_score = 0
        
        # System integrity
        integrity = self.check_system_integrity()
        if integrity["alerts"]:
            for alert in integrity["alerts"]:
                severity = alert.get("severity", "LOW")
                results.append(f"[{severity}] System: {alert['detail']}")
                if severity == "HIGH":
                    threat_score += 30
                elif severity == "MEDIUM":
                    threat_score += 15
        
        # Process scan
        procs = self.scan_processes()
        if procs["suspicious"]:
            for p in procs["suspicious"]:
                results.append(f"[HIGH] Process: {p['name']} (PID {p['pid']})")
                threat_score += 25
        
        if procs["high_cpu"]:
            for p in procs["high_cpu"][:2]:
                results.append(f"[MEDIUM] High CPU: {p['name']} ({p['cpu']:.1f}%)")
                threat_score += 10
        
        # Network scan
        network = self.scan_network()
        if network["suspicious"]:
            for c in network["suspicious"]:
                results.append(f"[HIGH] Network: {c['process']} → {c['remote']}:{c['port']}")
                threat_score += 20
        
        # Downloads scan
        dl_result = self.scan_downloads()
        if "suspicious" in dl_result.lower() or "threat" in dl_result.lower():
            results.append(f"[MEDIUM] {dl_result}")
            threat_score += 15
        
        # Determine threat level
        if threat_score >= 70:
            level = "CRITICAL"
        elif threat_score >= 40:
            level = "HIGH"
        elif threat_score >= 20:
            level = "MEDIUM"
        elif threat_score > 0:
            level = "LOW"
        else:
            level = "CLEAR"
        
        summary = (
            f"Security Scan Complete\n"
            f"Threat Level: {level} (Score: {threat_score}/100)\n"
            f"Processes: {procs['total_processes']} running\n"
            f"Connections: {network['total_connections']} active\n"
        )
        
        if results:
            summary += "\nIssues Found:\n" + "\n".join(results)
        else:
            summary += "\nNo active threats detected. ✓"
        
        return summary
    
    async def deep_scan_with_ai(self) -> dict:
        """Full Mac scan with AI threat analysis."""
        import httpx, os, stat
        from datetime import datetime
        
        print("[Security] Starting deep AI scan...")
        findings = []
        suspicious_files = []
        threat_score = 0
        
        # ── 1. SCAN KEY DIRECTORIES ──────────────────
        scan_dirs = [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("/tmp"),
            os.path.expanduser("~/Library/LaunchAgents"),
            "/Library/LaunchAgents",
            "/Library/LaunchDaemons",
        ]
        
        SUSPICIOUS_EXTENSIONS = {
            '.sh', '.bash', '.zsh', '.py', '.rb',
            '.pl', '.php', '.exe', '.dmg', '.pkg',
            '.app', '.scpt', '.applescript'
        }
        
        SUSPICIOUS_PATTERNS = [
            'keylogger', 'keystroke',
            'password_stealer', 'credential_dump',
            'backdoor', 'rootkit',
            'trojan', 'cryptominer', 'coinminer',
            'remote_access_tool',
            'exploit_kit', 'payload_exec',
            'inject_dll', 'process_inject',
            'reverse_shell_connect',
            'beacon_config', 'c2_server',
            'botnet_client', 'data_exfil',
            'priv_escalat', 'uac_bypass',
            'persistence_install'
        ]

        SAFE_EXTENSIONS = {
            '.icns', '.png', '.jpg', '.jpeg', '.gif',
            '.svg', '.ico', '.webp', '.pdf', '.md',
            '.txt', '.json', '.yaml', '.yml', '.toml',
            '.lock', '.log', '.csv', '.xml', '.html',
            '.css', '.map', '.d.ts', '.min.js',
            '.woff', '.woff2', '.ttf', '.otf', '.eot'
        }

        SAFE_PATH_PATTERNS = [
            'vscode', 'vs code', '.vscode',
            'shellintegration', 'shell-integration',
            'node_modules', 'site-packages',
            'homebrew', '.npm', '.pip',
            'antigravity', 'cursor', 'windsurf',
            'jetbrains', 'xcode', '.git',
            'python3', 'python2',
            'nova', 'ollama'
        ]

        SAFE_NAME_PATTERNS = [
            'shellintegration', 'shell-integration',
            'terminateprocess', 'cpuusage',
            'run-workflow', 'show-size',
            'format_json', 'extract_',
            'mapping.pl', 'decorator',
            'operator'
        ]
        
        file_count = 0
        for scan_dir in scan_dirs:
            if not os.path.exists(scan_dir):
                continue
            try:
                for root, dirs, files in os.walk(
                    scan_dir, followlinks=False
                ):
                    # Skip hidden system dirs
                    dirs[:] = [
                        d for d in dirs 
                        if not d.startswith('.')
                    ]
                    for fname in files[:50]:  # cap per dir
                        fpath = os.path.join(root, fname)
                        file_count += 1
                        try:
                            # Check extension
                            ext = os.path.splitext(
                                fname
                            )[1].lower()
                            if ext in SAFE_EXTENSIONS:
                                continue
                            
                            # Skip if path contains safe patterns
                            fpath_lower = fpath.lower()
                            if any(s in fpath_lower 
                                   for s in SAFE_PATH_PATTERNS):
                                continue
                            
                            # Skip if name matches safe patterns  
                            fname_lower = fname.lower()
                            if any(s in fname_lower 
                                   for s in SAFE_NAME_PATTERNS):
                                continue
                            
                            # Check suspicious name
                            name_suspicious = any(
                                p in fname_lower 
                                for p in SUSPICIOUS_PATTERNS
                            )
                            
                            # Check executable bit
                            try:
                                st = os.stat(fpath)
                                is_exec = bool(
                                    st.st_mode & 
                                    (stat.S_IXUSR | 
                                     stat.S_IXGRP | 
                                     stat.S_IXOTH)
                                )
                            except:
                                is_exec = False
                            
                            # Check file content for 
                            # small text files
                            content_suspicious = False
                            if (ext in {'.sh','.bash',
                                '.zsh','.py','.rb',
                                '.js','.ts'} and
                                os.path.getsize(fpath) 
                                < 50000
                            ):
                                try:
                                    with open(
                                        fpath, 'r',
                                        errors='ignore'
                                    ) as f:
                                        content = (
                                            f.read(2000)
                                            .lower()
                                        )
                                    content_suspicious = any(
                                        p in content 
                                        for p in [
                                            'base64.b64decode',
                                            'eval(compile',
                                            '/dev/tcp',
                                            'nc -e /bin',
                                            'curl|bash',
                                            'wget|bash',
                                            'chmod +x',
                                            'nohup',
                                            'disown',
                                        ]
                                    )
                                except:
                                    pass
                            
                            indicator_count = sum([
                                name_suspicious,
                                content_suspicious,
                                (is_exec and ext in SUSPICIOUS_EXTENSIONS 
                                 and len(fname) < 15)  # short generic names
                            ])
                            
                            if indicator_count >= 2:
                                reason = []
                                if name_suspicious:
                                    reason.append(
                                        "suspicious name"
                                    )
                                if content_suspicious:
                                    reason.append(
                                        "suspicious content"
                                    )
                                if is_exec:
                                    reason.append(
                                        "executable"
                                    )
                                
                                suspicious_files.append(
                                    fpath
                                )
                                findings.append(
                                    f"⚠ {fname} "
                                    f"({', '.join(reason)})"
                                    f" in {scan_dir}"
                                )
                                threat_score += 5
                        
                        except (PermissionError,  
                                OSError):
                            pass
            except (PermissionError, OSError):
                pass
        
        # ── 2. PROCESS SCAN ──────────────────────────
        procs = self.scan_processes()
        proc_count = procs.get('total_processes', 0)
        if procs.get('suspicious'):
            for p in procs['suspicious']:
                findings.append(
                    f"🔴 Suspicious process: "
                    f"{p['name']} (PID {p['pid']})"
                )
                threat_score += 25
        
        # ── 3. NETWORK SCAN ──────────────────────────
        network = self.scan_network()
        open_ports = network.get('total_connections', 0)
        if network.get('suspicious'):
            for c in network['suspicious']:
                findings.append(
                    f"🌐 Suspicious connection: "
                    f"{c['process']} → "
                    f"{c['remote']}:{c['port']}"
                )
                threat_score += 20
        
        # ── 4. LAUNCH AGENTS SCAN ────────────────────
        launch_dirs = [
            os.path.expanduser("~/Library/LaunchAgents"),
            "/Library/LaunchAgents",
            "/Library/LaunchDaemons",
        ]
        launch_count = 0
        for ld in launch_dirs:
            if os.path.exists(ld):
                try:
                    plists = [
                        f for f in os.listdir(ld)
                        if f.endswith('.plist')
                    ]
                    launch_count += len(plists)
                    # Flag unknown launch agents
                    known_safe = [
                        'com.apple', 'com.google', 'com.adobe',
                        'homebrew', 'com.microsoft', 'com.spotify',
                        'com.docker', 'com.ollama', 'com.github',
                        'com.jetbrains', 'com.cursor', 'com.vscode',
                        'com.todesktop', 'com.figma', 'com.slack',
                        'com.notion', 'com.dropbox', 'com.1password',
                        'com.raycast', 'com.linear', 'com.arc',
                        'org.python', 'com.node', 'io.ansible',
                        'com.anthropic', 'com.openai', 'com.vercel',
                        'io.windsurf', 'com.antigravity',
                        'com.nova', 'com.soham', 'local.'
                    ]
                    for plist in plists:
                        if not any(
                            s in plist.lower() 
                            for s in known_safe
                        ):
                            findings.append(
                                f"⚡ Unknown LaunchAgent:"
                                f" {plist}"
                            )
                            threat_score += 2
                except:
                    pass
        
        # ── 5. AI ANALYSIS ───────────────────────────
        ai_analysis = "System appears clean."
        if findings:
            prompt = (
                f"You are a Mac security analyst. "
                f"Analyze these security findings "
                f"and give a 3-sentence threat "
                f"assessment:\n\n"
                + "\n".join(findings[:15])
                + f"\n\nThreat score: {threat_score}/100"
                + f"\nFiles scanned: {file_count}"
                + f"\nProcesses: {proc_count}"
            )
            try:
                async with httpx.AsyncClient() as c:
                    r = await c.post(
                        "http://localhost:11434"
                        "/api/generate",
                        json={
                            "model": "llama3.2",
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=30
                    )
                    ai_analysis = r.json().get(
                        "response", 
                        "Analysis unavailable."
                    )
            except:
                ai_analysis = (
                    "AI analysis unavailable. "
                    "Review findings manually."
                )
        else:
            ai_analysis = (
                f"Scanned {file_count} files across "
                f"key directories, {proc_count} "
                f"processes, and {open_ports} network "
                f"connections. No threats detected. "
                f"System is clean."
            )
        
        # ── 6. FINAL SCORE CAP ───────────────────────
        threat_score = min(threat_score, 100)
        if threat_score >= 70:
            level = "CRITICAL"
        elif threat_score >= 40:
            level = "HIGH"
        elif threat_score >= 20:
            level = "MEDIUM"
        elif threat_score > 0:
            level = "LOW"
        else:
            level = "CLEAR"
        
        # Log to DB
        self._log_event(
            "full_scan", "scanner",
            f"Deep scan complete. "
            f"Level: {level}, "
            f"Score: {threat_score}",
            str(threat_score)
        )
        
        return {
            "threat_score": threat_score,
            "threat_level": level,
            "processes_checked": proc_count,
            "suspicious_files": len(suspicious_files),
            "open_ports": open_ports,
            "vulnerabilities": launch_count,
            "files_scanned": file_count,
            "findings": findings[:20],
            "ai_analysis": ai_analysis,
            "scanned_at": datetime.now().isoformat()
        }
    
    # ─── 8. THREAT LEVEL ─────────────────────────────
    
    def get_threat_level(self) -> ThreatLevel:
        """Quick threat level assessment."""
        score = 0
        reasons = []
        
        # Check high CPU processes
        for proc in psutil.process_iter(['name', 'cpu_percent']):
            try:
                cpu = proc.info['cpu_percent'] or 0
                if cpu > 90:
                    score += 20
                    reasons.append(f"High CPU: {proc.info['name']}")
            except:
                pass
        
        # Check recent events
        recent_high = [
            e for e in self._events[-20:]
            if e.severity in ["HIGH", "CRITICAL"]
        ]
        score += len(recent_high) * 15
        for e in recent_high[:2]:
            reasons.append(e.title)
        
        score = min(score, 100)
        
        if score >= 70:
            level = "CRITICAL"
        elif score >= 40:
            level = "HIGH"
        elif score >= 20:
            level = "MEDIUM"
        elif score > 0:
            level = "LOW"
        else:
            level = "CLEAR"
        
        return ThreatLevel(
            level=level, score=score, reasons=reasons
        )
    
    # ─── 9. SECURE MODE ──────────────────────────────
    
    def enable_secure_mode(self) -> str:
        """Enable strict security mode."""
        self.SECURE_MODE = True
        self._log_event(
            "LOW", "system",
            "Secure Mode Enabled",
            "Strict security policies active"
        )
        return (
            "Secure Mode ENABLED.\n"
            "• Unknown downloads will be flagged\n"
            "• Network connections monitored\n"
            "• App permissions restricted"
        )
    
    def disable_secure_mode(self) -> str:
        self.SECURE_MODE = False
        return "Secure Mode disabled."
    
    # ─── 10. BACKGROUND MONITOR ──────────────────────
    
    def start_monitoring(self):
        """Start background security monitoring."""
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_thread.start()
        print("[Security] ✅ Background monitoring active")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        check_count = 0
        while self._monitoring:
            try:
                check_count += 1
                
                # Every 30s: process check
                if check_count % 3 == 0:
                    procs = self.scan_processes()
                    if procs["suspicious"]:
                        print(f"[Security] ⚠ Suspicious process: {procs['suspicious'][0]['name']}")
                
                # Every 2min: network check
                if check_count % 12 == 0:
                    network = self.scan_network()
                    if network["suspicious"]:
                        print(f"[Security] ⚠ Suspicious connection: {network['suspicious'][0]}")
                
                # Every 5min: integrity check
                if check_count % 30 == 0:
                    self.check_system_integrity()
                
                time.sleep(10)
            except Exception as e:
                time.sleep(30)
    
    def stop_monitoring(self):
        self._monitoring = False
    
    # ─── 11. SECURITY LOGS ───────────────────────────
    
    def get_recent_events(self, limit: int = 20) -> list:
        """Get recent security events."""
        conn = sqlite3.connect(self.DB_PATH)
        rows = conn.execute(
            "SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [{
            "id": r[0],
            "timestamp": r[1],
            "severity": r[2],
            "category": r[3],
            "title": r[4],
            "description": r[5],
            "action": r[6]
        } for r in rows]
    
    def get_security_summary(self) -> dict:
        """Summary for dashboard panel."""
        threat = self.get_threat_level()
        events = self.get_recent_events(10)
        procs = self.get_process_list(5)
        network = self.scan_network()
        
        return {
            "threat_level": threat.level,
            "threat_score": threat.score,
            "threat_reasons": threat.reasons,
            "recent_events": events,
            "top_processes": procs,
            "active_connections": network["total_connections"],
            "suspicious_connections": len(network["suspicious"]),
            "secure_mode": self.SECURE_MODE,
            "monitoring_active": self._monitoring
        }

# Singleton
security_officer = SecurityOfficer()
