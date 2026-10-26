import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login, saveToken } from "../api";
import ThemeToggle from "../components/ThemeToggle";
import logo from "../assets/logo.png";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!username.trim() || !password) {
      setError("Please enter both username and password.");
      return;
    }

    setLoading(true);
    try {
      const data = await login(username.trim(), password);
      saveToken(data.token);
      navigate("/home");
    } catch (err) {
      const message = err.response?.data?.error || "Login failed. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-layout">
      {/* Left Visual Banner with Main Logo */}
      <section className="auth-visual">
        <div className="auth-brand">
          <span className="brand-mark overflow-hidden bg-transparent" style={{ width: 56, height: 56 }}>
            <img src={logo} alt="VeriSight Logo" className="w-full h-full object-contain" />
          </span>
          <span><b>VeriSight</b><small>TRUST INTELLIGENCE</small></span>
        </div>
        <div className="auth-visual-content">
          <span className="welcome-tag"><i/> A CLEARER VIEW OF DIGITAL CONTENT</span>
          <h1>Truth deserves<br/><em>a closer look.</em></h1>
          <p>Investigate suspicious claims and media with a unified AI-powered verification workspace.</p>
          <div className="auth-feature-list">
            <div><span>◈</span><div><b>Four focused detectors</b><small>Text, news, images and video</small></div></div>
            <div><span>⌕</span><div><b>Context-aware insights</b><small>Understand signals behind results</small></div></div>
            <div><span>↗</span><div><b>Your own analysis history</b><small>Keep past checks in one place</small></div></div>
          </div>
        </div>
        <div className="auth-visual-footer">
          <span>BUILT FOR A MORE INFORMED INTERNET</span>
        </div>
        <div className="auth-orb auth-orb-one"/><div className="auth-orb auth-orb-two"/>
      </section>

      {/* Right Form Side */}
      <section className="auth-form-side">
        <ThemeToggle className="theme-button auth-theme"/>
        <div className="auth-form-wrap">
          <span className="section-kicker">WELCOME BACK</span>
          <h2>Sign in to your workspace</h2>
          <p className="auth-subtitle">Continue where your investigation left off.</p>

          {error && <div className="error-banner"><span>!</span>{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="field-block">
              <label htmlFor="login-username">Username</label>
              <input id="login-username" type="text" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} placeholder="Enter your username"/>
            </div>
            <div className="field-block">
              <label htmlFor="login-password">Password</label>
              <input id="login-password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter your password"/>
            </div>
            <button type="submit" disabled={loading} className="primary-button auth-submit">
              {loading ? <><span className="spinner"/> Signing you in…</> : <>Sign in securely <span>↗</span></>}
            </button>
          </form>

          <p className="auth-switch">New to VeriSight? <Link to="/signup">Create an account <span>→</span></Link></p>
          <div className="auth-safe-note"><span>⌑</span> Your workspace is protected by account authentication.</div>
        </div>
        <div className="auth-copyright">© 2026 VERISIGHT <span>•</span> AI-ASSISTED VERIFICATION</div>
      </section>
    </div>
  );
}