import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getHistory } from "../api";
import VerdictBadge from "../components/VerdictBadge";
import AppShell from "../components/AppShell";
function formatDate(value) { const date = new Date(value); return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }
function typeLabel(type) { return ({ text: 'Text analysis', image: 'Image analysis', video: 'Video analysis' })[type] || type || 'Scan'; }
function typeIcon(type) { return ({ text: 'Tt', image: '▧', video: '▷' })[type] || '◈'; }
export default function History() {
  const [entries, setEntries] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const navigate = useNavigate();
  useEffect(() => { getHistory().then(data => setEntries(data.history || [])).catch(err => { if (err.response?.status === 401) { navigate('/'); return; } setError('Could not load history. Please try again.'); }).finally(() => setLoading(false)); }, [navigate]);
  return <AppShell active="history" title="Scan history" eyebrow="YOUR ACTIVITY">
    <div className="history-heading"><div><h1>Past analyses</h1><p>Review previous submissions and their model predictions.</p></div><button className="primary-button" onClick={() => navigate('/scan')}>New analysis <span>↗</span></button></div>
    <div className="history-summary"><div><span className="summary-symbol">◷</span><span><small>Saved analyses</small><b>{loading ? '—' : entries.length}</b></span></div><div><span className="summary-symbol blue">⌕</span><span><small>History storage</small><b>Personal</b></span></div><div className="history-summary-note">Your scan records are associated with your account.</div></div>
    {loading && <div className="panel history-empty"><span className="spinner large-spinner"/><p>Loading your history…</p></div>}
    {error && <div className="error-banner">{error}</div>}
    {!loading && !error && entries.length === 0 && <div className="panel history-empty"><span className="empty-illustration">◷</span><h2>Your history starts here</h2><p>Once you analyze content, your past scans and results will appear here.</p><button className="primary-button" onClick={() => navigate('/scan')}>Run your first analysis <span>↗</span></button></div>}
    {!loading && !error && entries.length > 0 && <div className="history-list">{entries.map((entry, i) => <article className="panel history-entry" key={entry.id ?? `${entry.created_at}-${i}`}><div className="history-entry-top"><div className="history-type"><span className={`history-type-icon ${entry.type || 'text'}`}>{typeIcon(entry.type)}</span><div><b>{typeLabel(entry.type)}</b><small>Scan ID · {entry.id ?? '—'}</small></div></div><time>{formatDate(entry.created_at)}</time></div><p className="history-preview">{entry.preview || 'No preview available for this submission.'}</p><div className="history-verdicts"><VerdictBadge label="Fake news" verdict={entry.fake_news_verdict} confidence={entry.fake_news_confidence}/><VerdictBadge label="AI text" verdict={entry.ai_text_verdict} confidence={entry.ai_text_confidence}/><VerdictBadge label="Deepfake" verdict={entry.deepfake_verdict} confidence={entry.deepfake_confidence}/><VerdictBadge label="AI image" verdict={entry.ai_image_verdict} confidence={entry.ai_image_confidence}/></div></article>)}</div>}
  </AppShell>;
}
