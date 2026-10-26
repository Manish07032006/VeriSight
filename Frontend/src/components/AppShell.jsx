import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { clearToken, getCurrentUser } from "../api";
import ThemeToggle from "./ThemeToggle";
import logo from "../assets/logo.png";

const Icon = ({ name, size = 19 }) => {
  const paths = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    scan: <><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/><path d="M8 10.8h5.6M10.8 8v5.6"/></>,
    history: <><path d="M3 12a9 9 0 1 0 2.6-6.4L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    logout: <><path d="M10 17l5-5-5-5M15 12H3"/><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"/></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
};

export { Icon };

export default function AppShell({ children, active = "overview", title = "Overview", eyebrow = "WORKSPACE" }) {
  const [user, setUser] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  useEffect(() => { getCurrentUser().then(d => setUser(d.user)).catch(() => {}); }, []);
  const logout = () => { clearToken(); navigate("/"); };
  return <div className="app-layout">
    <aside className="sidebar">
      {/* ── CHANGED FROM SHIELD ICON TO CUSTOM LOGO IMAGE ── */}
      <button className="brand-lockup" onClick={() => navigate('/home')} aria-label="VeriSight home">
  <span className="brand-mark overflow-hidden bg-transparent" style={{ width: 46, height: 46, minWidth: 46 }}>
    <img src={logo} alt="VeriSight Logo" className="w-full h-full object-contain" />
  </span>
  <span className="brand-copy">
    <b>VeriSight</b>
    <small>TRUST INTELLIGENCE</small>
  </span>
</button>

      <div className="side-label">MAIN MENU</div>
      <nav className="side-nav">
        <NavLink to="/home" className={active === 'overview' ? 'side-link active' : 'side-link'}><Icon name="overview"/><span>Overview</span></NavLink>
        <NavLink to="/scan" className={active === 'scan' ? 'side-link active' : 'side-link'}><Icon name="scan"/><span>New analysis</span><span className="nav-plus">+</span></NavLink>
        <NavLink to="/history" className={active === 'history' ? 'side-link active' : 'side-link'}><Icon name="history"/><span>Scan history</span></NavLink>
      </nav>
      <div className="sidebar-spacer"/>
      <div className="sidebar-status"><span className="status-pulse"/><div><b>Detection system</b><small>Ready for analysis</small></div></div>
      <button className="side-link logout-link" onClick={logout}><Icon name="logout"/><span>Sign out</span></button>
      <div className="sidebar-footer">AI-POWERED VERIFICATION <span>•</span> V1.0</div>
    </aside>
    <main className="main-panel">
      <header className="topbar">
        <div className="breadcrumb"><span>VeriSight</span><b>/</b><strong>{title}</strong></div>
        <div className="topbar-actions"><span className="secure-pill"><i/> Secure workspace</span><ThemeToggle className="theme-button"/>
          <div className="profile-wrap"><button className="profile-button" onClick={() => setMenuOpen(v => !v)}><span className="avatar">{(user?.username || 'U').slice(0,1).toUpperCase()}</span><span className="profile-name"><b>{user?.username || 'Your account'}</b><small>Personal workspace</small></span><span className="chevron">⌄</span></button>
          {menuOpen && <div className="profile-menu"><button onClick={() => { setMenuOpen(false); navigate('/history'); }}>Scan history</button><button onClick={logout}>Sign out</button></div>}</div>
        </div>
      </header>
      <div className="page-content"><div className="page-eyebrow">{eyebrow}</div>{children}</div>
    </main>
  </div>;
}