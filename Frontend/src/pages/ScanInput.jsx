import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { scanText, scanMedia } from "../api";
import VerdictBadge from "../components/VerdictBadge";
import AppShell from "../components/AppShell";

const TABS = [
  { id: "text", label: "Text & news", icon: "Tt" },
  { id: "image", label: "Image", icon: "▧" },
  { id: "video", label: "Video", icon: "▷" },
];

function normalizeResponse(response) {
  const data = response?.data ?? response;

  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("The server returned an invalid response.");
  }

  return data;
}

function formatLabel(value) {
  if (!value) return "Unavailable";

  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatConfidence(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "Unavailable";
  }

  return `${value.toFixed(2)}%`;
}

function TrustIndexBanner({ trustIndex }) {
  if (!trustIndex) return null;

  const probability = trustIndex.overall_synthetic_probability ?? 0;
  
  const isHighRisk = probability >= 70;
  const isModerateRisk = probability >= 40 && probability < 70;

  const badgeColorClass = isHighRisk
    ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
    : isModerateRisk
    ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
    : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";

  const barColorClass = isHighRisk
    ? "bg-rose-500"
    : isModerateRisk
    ? "bg-amber-500"
    : "bg-emerald-500";

  return (
    <div className="panel p-5 rounded-xl border border-slate-800 mb-4 bg-slate-900/60 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="section-kicker">VERISIGHT SUMMARY</span>
          <h3 className="text-xl font-semibold text-white mt-1">
            Overall Trust Score
          </h3>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-bold border ${badgeColorClass}`}>
          {trustIndex.verdict}
        </span>
      </div>

      <div className="flex items-center justify-between text-sm mb-2">
        <span className="text-slate-400">Estimated AI-Generated Likelihood</span>
        <span className="font-bold text-white text-lg">{probability}%</span>
      </div>

      <div className="w-full h-2.5 rounded-full bg-slate-800 overflow-hidden mb-3">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${barColorClass}`}
          style={{ width: `${probability}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Combined analysis from all active AI detectors</span>
        <span className="capitalize">Risk Level: {trustIndex.risk_level?.replace(/_/g, " ")}</span>
      </div>
    </div>
  );
}

function EvidenceReport({ result }) {
  const evidence = result.evidence_assessment;

  if (!evidence) return null;

  const overallStatus = evidence.overall_status;
  const overallDescriptions = {
    potentially_synthetic_or_manipulated:
      "One or more available checks flagged a potential concern. Further verification is recommended.",
    no_issue_detected_by_available_models:
      "The available models did not flag a concern. This does not prove that the media is authentic.",
    inconclusive:
      "The available evidence is insufficient to reach a meaningful conclusion.",
  };

  return (
    <section className="panel p-5 rounded-xl mt-4">
      <span className="section-kicker">EVIDENCE REVIEW</span>

      <h3 className="text-xl font-semibold text-white mt-2 mb-2">
        Overall assessment
      </h3>

      <p className="text-base font-semibold text-slate-200 mb-2">
        {formatLabel(overallStatus)}
      </p>

      <p className="text-sm text-slate-400 mb-5">
        {overallDescriptions[overallStatus] ||
          evidence.explanation ||
          "Review the individual checks and their limitations."}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {evidence.ai_image_detection && (
          <StatusCard
            title="AI-image detection"
            status={evidence.ai_image_detection.status}
            description={`Verdict: ${formatLabel(
              evidence.ai_image_detection.verdict
            )} · Model score: ${formatConfidence(
              evidence.ai_image_detection.model_score
            )}`}
          />
        )}

        {evidence.deepfake_detection && (
          <StatusCard
            title="Face-manipulation detection"
            status={evidence.deepfake_detection.status}
            description={`Verdict: ${formatLabel(
              evidence.deepfake_detection.verdict
            )} · Model score: ${formatConfidence(
              evidence.deepfake_detection.model_score
            )}`}
          />
        )}

        {evidence.provenance && (
          <StatusCard
            title="Content credentials (C2PA)"
            status={evidence.provenance.status}
            description={evidence.provenance.message}
          />
        )}

        {evidence.local_visual_search && (
          <StatusCard
            title="Local visual search"
            status={evidence.local_visual_search.status}
            description={`${evidence.local_visual_search.message} Reference images scanned: ${
              evidence.local_visual_search.reference_images_scanned ?? 0
            }.`}
          />
        )}
      </div>
    </section>
  );
}

function StatusCard({ title, status, description }) {
  return (
    <div className="panel p-4 rounded-xl border border-slate-800">
      <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">
        {title}
      </p>
      <h3 className="text-lg font-semibold text-white mb-2">
        {formatLabel(status)}
      </h3>
      {description && <p className="text-sm text-slate-400">{description}</p>}
    </div>
  );
}

function ManualSearchLinks({ result }) {
  const search = result.manual_search_links;

  if (!search?.search_pages?.length) return null;

  return (
    <section className="panel p-5 rounded-xl mt-4">
      <h3 className="text-lg font-semibold text-white mb-2">
        Manual reverse-image search
      </h3>
      <p className="text-sm text-slate-400 mb-4">{search.message}</p>
      <div className="flex flex-wrap gap-3">
        {search.search_pages.map((item) => (
          <a
            key={item.provider}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="primary-button inline-flex items-center gap-2"
          >
            {item.provider}
            <span>↗</span>
          </a>
        ))}
      </div>
    </section>
  );
}

export default function ScanInput() {
  const location = useLocation();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState(
    location.state?.tab === "media"
      ? "image"
      : location.state?.tab || "text"
  );

  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  function resetFeedback() {
    setError("");
    setResult(null);
  }

  function handleTabChange(tabId) {
    if (loading) return;
    setActiveTab(tabId);
    setFile(null);
    setPreviewUrl(null);
    resetFeedback();
  }

  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0] || null;
    setFile(selectedFile);
    setPreviewUrl(selectedFile ? URL.createObjectURL(selectedFile) : null);
    resetFeedback();
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    resetFeedback();

    if (activeTab === "text" && !text.trim()) {
      setError("Please enter some text to verify.");
      return;
    }

    if (activeTab !== "text" && !file) {
      setError(`Please choose ${activeTab === "image" ? "an image" : "a video"} file first.`);
      return;
    }

    setLoading(true);

    try {
      const response =
        activeTab === "text"
          ? await scanText(text.trim())
          : await scanMedia(file);

      const data = normalizeResponse(response);

      if (data.error) {
        throw new Error(data.error);
      }

      setResult(data);
    } catch (err) {
      if (err.response?.status === 401) {
        navigate("/");
        return;
      }
      setError(err.response?.data?.error || err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  const isMediaResult =
    result?.media_type === "image" || result?.media_type === "video";

  const backendBaseUrl = (
    import.meta.env.VITE_API_URL || "http://127.0.0.1:5000"
  ).replace(/\/+$/, "");

  const mediaUrl = result?.file_url
    ? /^https?:\/\//i.test(result.file_url)
      ? result.file_url
      : `${backendBaseUrl}/${result.file_url.replace(/^\/+/, "")}`
    : null;

  return (
    <AppShell active="scan" title="New analysis" eyebrow="CONTENT INSPECTION">
      <div className="scan-heading">
        <div>
          <h1>Let’s inspect the details.</h1>
          <p>Submit text or media to run it through your detection models.</p>
        </div>
        <div className="scan-secure">
          <span className="status-pulse" /> PRIVATE SESSION
        </div>
      </div>

      <div className="scan-layout">
        <section className="panel scan-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">STEP 01 / SUBMISSION</span>
              <h2>What would you like to check?</h2>
            </div>
          </div>

          <div className="scan-tabs">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => handleTabChange(tab.id)}
                disabled={loading}
                className={activeTab === tab.id ? "scan-tab active" : "scan-tab"}
              >
                <span className="tab-icon">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit}>
            {activeTab === "text" ? (
              <div className="field-block">
                <div className="field-title">
                  <label htmlFor="scan-text">Text content</label>
                  <span>NEWS · CLAIMS · ARTICLES</span>
                </div>
                <textarea
                  id="scan-text"
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  placeholder="Paste a headline, article, social post, or claim you want to verify…"
                  rows={9}
                  disabled={loading}
                />
              </div>
            ) : (
              <div className="upload-zone">
                <input
                  id="media-upload"
                  type="file"
                  accept={activeTab === "image" ? ".jpg,.jpeg,.png,.webp" : ".mp4,.mov"}
                  onChange={handleFileChange}
                  disabled={loading}
                />
                <label htmlFor="media-upload" className="upload-content">
                  {previewUrl ? (
                    <div className="w-full flex flex-col items-center">
                      {activeTab === "image" ? (
                        <img src={previewUrl} alt="Preview" className="max-h-40 rounded-lg object-contain mb-2 border border-slate-700" />
                      ) : (
                        <video src={previewUrl} className="max-h-40 rounded-lg object-contain mb-2 border border-slate-700" controls />
                      )}
                      <strong className="text-xs">{file?.name}</strong>
                    </div>
                  ) : (
                    <>
                      <span className="upload-icon">{activeTab === "image" ? "▧" : "▷"}</span>
                      <strong>Drop your {activeTab} here</strong>
                      <span>or click to browse files from your device</span>
                    </>
                  )}
                  <span className="browse-button">Browse files</span>
                </label>
              </div>
            )}

            {error && (
              <div className="error-banner" role="alert">
                <span>!</span> {error}
              </div>
            )}

            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={loading}>
                {loading ? <><span className="spinner" /> Analyzing content…</> : <>Run detection <span>↗</span></>}
              </button>
            </div>
          </form>
        </section>

        <aside className="scan-aside">
          <div className="panel pipeline-panel">
            <span className="section-kicker">THE PROCESS</span>
            <h3>Four signals. One clearer picture.</h3>
          </div>
        </aside>
      </div>

      {result && (
        <section className="results-section" id="results">
          <div className="results-title">
            <div>
              <span className="section-kicker">ANALYSIS COMPLETE</span>
              <h2>Your verification report</h2>
            </div>
            <span className="complete-pill"><i /> Results received</span>
          </div>

          {mediaUrl && (
            <div className="panel p-4 mb-4 text-center bg-slate-900/40 border border-slate-800 rounded-xl">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                Analyzed Media Preview
              </p>
              {result.media_type === "image" ? (
                <img src={mediaUrl} alt="Analyzed target" className="max-h-72 rounded-lg mx-auto object-contain shadow-md" />
              ) : (
                <video src={mediaUrl} className="max-h-72 rounded-lg mx-auto shadow-md" controls />
              )}
            </div>
          )}

          {isMediaResult ? (
            <>
              <TrustIndexBanner trustIndex={result.verisight_trust_index} />

              <div className="results-grid">
                <VerdictBadge
                  label="Deepfake check"
                  verdict={result.deepfake_verdict}
                  confidence={result.deepfake_confidence}
                />
                <VerdictBadge
                  label="AI-image check"
                  verdict={result.ai_image_verdict}
                  confidence={result.ai_image_confidence}
                  color={result.ai_image_color}
                />
              </div>

              <EvidenceReport result={result} />
              <ManualSearchLinks result={result} />
            </>
          ) : (
            <>
              <div className="results-grid">
                <VerdictBadge
                  label="Fake news check"
                  verdict={result.fake_news_verdict}
                  confidence={result.fake_news_confidence}
                />
                <VerdictBadge
                  label="AI-text check"
                  verdict={result.ai_text_verdict}
                  confidence={result.ai_text_confidence}
                />
              </div>

              {result.explanation && (
                <div className="explanation-panel">
                  <div className="explanation-heading">
                    <span>✦</span>
                    <div>
                      <b>Analysis explanation & context</b>
                      <small>Powered by Tavily search intelligence</small>
                    </div>
                  </div>
                  <p>{result.explanation}</p>
                  {result.sources_checked > 0 && (
                    <span className="source-count">
                      Checked {result.sources_checked} web sources for verification.
                    </span>
                  )}
                </div>
              )}
            </>
          )}
        </section>
      )}
    </AppShell>
  );
}