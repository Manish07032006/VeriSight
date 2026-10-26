import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signup, saveToken } from "../api";
import ThemeToggle from "../components/ThemeToggle";
import logo from "../assets/logo.png";

export default function Signup() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!username.trim() || !email.trim() || !password) {
      setError("All fields are required.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);
    try {
      const data = await signup(username.trim(), email.trim(), password);
      saveToken(data.token);
      navigate("/home");
    } catch (err) {
      const message = err.response?.data?.error || "Signup failed. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-layout">
      {/* Left Visual Banner with Main Logo */}
      <section className="auth-visual signup-visual">
        <div className="auth-brand">
          <span className="brand-mark overflow-hidden bg-transparent" style={{ width: 56, height: 56 }}>
            <img src={logo} alt="VeriSight Logo" className="w-full h-full object-contain" />
          </span>
          <span><b>VeriSight</b><small>TRUST INTELLIGENCE</small></span>
        </div>
        <div className="auth-visual-content">
          <span className="welcome-tag"><i/> START WITH CLARITY</span>
          <h1>Build trust<br/><em>into every check.</em></h1>
          <p>Create your personal workspace to examine content, review model signals, and keep your analyses together.</p>
          <div className="auth-feature-list">
            <div><span>✳</span><div><b>One connected workspace</b><small>All four detection tools in one place</small></div></div>
            <div><span>◷</span><div><b>History that stays organized</b><small>Return to your previous checks</small></div></div>
            <div><span>✧</span><div><b>Explanations with context</b><small>Interpret results more thoughtfully</small></div></div>
          </div>
        </div>
        <div className="auth-visual-footer">
          <span>LOOK CLOSER. THINK CLEARER.</span>
        </div>
        <div className="auth-orb auth-orb-one"/><div className="auth-orb auth-orb-two"/>
      </section>

      {/* Right Form Side */}
      <section className="auth-form-side">
        <ThemeToggle className="theme-button auth-theme"/>
        <div className="auth-form-wrap">
          <span className="section-kicker">CREATE YOUR ACCOUNT</span>
          <h2>Your workspace starts here</h2>
          <p className="auth-subtitle">A few details and you’re ready to begin.</p>

          {error && <div className="error-banner"><span>!</span>{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="field-block">
              <label htmlFor="signup-username">Username</label>
              <input id="signup-username" type="text" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} placeholder="Choose a username"/>
            </div>
            <div className="field-block">
              <label htmlFor="signup-email">Email address</label>
              <input id="signup-email" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com"/>
            </div>
            <div className="field-block">
              <label htmlFor="signup-password">Password</label>
              <input id="signup-password" type="password" autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)} placeholder="At least 6 characters"/>
              <small className="field-hint">Use at least 6 characters.</small>
            </div>
            <button type="submit" disabled={loading} className="primary-button auth-submit">
              {loading ? <><span className="spinner"/> Creating account…</> : <>Create account <span>↗</span></>}
            </button>
          </form>

          <p className="auth-switch">Already have an account? <Link to="/">Sign in <span>→</span></Link></p>
          <div className="auth-safe-note"><span>⌑</span> Your workspace is personal to your account.</div>
        </div>
        <div className="auth-copyright">© 2026 VERISIGHT <span>•</span> AI-ASSISTED VERIFICATION</div>
      </section>
    </div>
  );
}