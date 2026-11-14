import React, { useState } from 'react';
import {
  X,
  ArrowLeft,
  Download,
  Share2,
  FileText,
  Eye,
  ShieldAlert,
  CloudRain,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  Info,
  Layers,
  Columns
} from 'lucide-react';

function normalizeImageUrl(path) {
  if (!path) return null;
  if (path.startsWith('data:') || path.startsWith('blob:') || path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const clean = path.replace(/\\/g, '/').replace(/^\/+/, '');
  return `/${clean}`;
}

export default function ArtifactPanel({
  isOpen,
  onClose,
  diagResult,
  imagePreview,
  weatherData,
  lang,
  t,
  onDownloadPdf,
  pdfDownloading,
  onOpenKvkModal
}) {
  const [activeTab, setActiveTab] = useState('xai'); // 'xai' | 'advisory' | 'weather' | 'kvk'
  const [comparisonMode, setComparisonMode] = useState('split'); // 'split' | 'slider'
  const [overlayOpacity, setOverlayOpacity] = useState(65); // 0 = only leaf, 100 = full heatmap

  if (!isOpen || !diagResult) return null;

  const crop = diagResult.crop || 'sugarcane';
  const diseaseName = diagResult.disease_name_multilingual?.[lang] || diagResult.predicted_class;
  const confidencePct = ((diagResult.confidence || 0) * 100).toFixed(1);
  const advisory = diagResult.details?.contextual_advisory || {};
  const multimodal = diagResult.details?.multimodal_assessment?.multimodal_assessment || {};
  const sprayWindow = weatherData?.spray_window || {};
  const heatmapUrl = normalizeImageUrl(diagResult.heatmap_path);
  const leafUrl = normalizeImageUrl(imagePreview);

  return (
    <aside className="claude-artifact-panel">
      {/* Artifact Header */}
      <div className="artifact-header">
        <div className="artifact-header-title">
          <button
            className="artifact-back-btn"
            onClick={onClose}
            title="Back to conversation"
          >
            <ArrowLeft size={18} />
          </button>
          <div className="artifact-doc-icon desktop-icon">
            <FileText size={18} />
          </div>
          <div>
            <h3 title={`${crop.toUpperCase()} - ${diseaseName}`}>
              {diseaseName}
            </h3>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              {diagResult.model_version || (diagResult.is_local_inference ? 'Edge WASM INT8' : 'Cloud PyTorch 2.x')}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <button
            className="topbar-btn"
            onClick={onDownloadPdf}
            disabled={pdfDownloading}
            style={{
              background: 'var(--accent-green)',
              color: '#ffffff',
              borderColor: 'transparent',
              fontWeight: 600
            }}
            title="Download official PDF report"
          >
            <Download size={13} />
            <span>{pdfDownloading ? '...' : 'PDF'}</span>
          </button>

          <button
            className="modal-close-btn desktop-only"
            onClick={onClose}
            title="Close Artifact Canvas"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Artifact Navigation Tabs */}
      <div className="artifact-nav-tabs">
        <button
          className={`artifact-tab-btn ${activeTab === 'xai' ? 'active' : ''}`}
          onClick={() => setActiveTab('xai')}
        >
          <Eye size={14} />
          <span>{lang === 'mr' ? 'Grad-CAM दृश्य' : 'Visual XAI'}</span>
        </button>

        <button
          className={`artifact-tab-btn ${activeTab === 'advisory' ? 'active' : ''}`}
          onClick={() => setActiveTab('advisory')}
        >
          <FileText size={14} />
          <span>{lang === 'mr' ? 'उपचार सल्ला' : 'ICAR Advisory'}</span>
        </button>

        <button
          className={`artifact-tab-btn ${activeTab === 'weather' ? 'active' : ''}`}
          onClick={() => setActiveTab('weather')}
        >
          <CloudRain size={14} />
          <span>{lang === 'mr' ? 'हवामान व फवारणी' : 'Spray Window'}</span>
        </button>

        <button
          className={`artifact-tab-btn ${activeTab === 'kvk' ? 'active' : ''}`}
          onClick={() => setActiveTab('kvk')}
        >
          <UserCheck size={14} />
          <span>{lang === 'mr' ? 'KVK तज्ज्ञ' : 'KVK Expert'}</span>
        </button>
      </div>

      {/* Artifact Scrollable Body */}
      <div className="artifact-scrollable-body">
        {/* Metric Summary Pill Bar */}
        <div className="metric-summary-bar">
          <div className="metric-pill-item">
            <span>Crop</span>
            <strong style={{ textTransform: 'capitalize' }}>{crop}</strong>
          </div>
          <div className="metric-pill-item">
            <span>Confidence</span>
            <strong style={{ color: diagResult.confidence >= 0.75 ? 'var(--accent-green)' : 'var(--accent-terracotta)' }}>
              {confidencePct}%
            </strong>
          </div>
          <div className="metric-pill-item">
            <span>Severity</span>
            <strong>{diagResult.details?.severity || 'MODERATE'}</strong>
          </div>
        </div>

        {/* TAB 1: Visual Explainability (Grad-CAM) */}
        {activeTab === 'xai' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {/* View Mode Switcher: Side-by-Side vs Interactive Opacity Slider */}
            {heatmapUrl && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                  View Mode:
                </span>
                <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                  <button
                    onClick={() => setComparisonMode('split')}
                    style={{
                      border: 'none',
                      background: comparisonMode === 'split' ? 'var(--bg-card)' : 'transparent',
                      color: comparisonMode === 'split' ? 'var(--text-primary)' : 'var(--text-muted)',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      boxShadow: comparisonMode === 'split' ? 'var(--shadow-sm)' : 'none'
                    }}
                  >
                    <Columns size={12} /> Side-by-Side
                  </button>

                  <button
                    onClick={() => setComparisonMode('slider')}
                    style={{
                      border: 'none',
                      background: comparisonMode === 'slider' ? 'var(--bg-card)' : 'transparent',
                      color: comparisonMode === 'slider' ? 'var(--text-primary)' : 'var(--text-muted)',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      boxShadow: comparisonMode === 'slider' ? 'var(--shadow-sm)' : 'none'
                    }}
                  >
                    <Layers size={12} /> Opacity Overlay
                  </button>
                </div>
              </div>
            )}

            {/* Split View */}
            {comparisonMode === 'split' && (
              <div className="xai-preview-grid">
                <div className="xai-panel-box">
                  <span>{t.originalLeaf}</span>
                  <div className="xai-img-frame">
                    <img src={leafUrl} alt="Original Leaf" />
                  </div>
                </div>

                <div className="xai-panel-box">
                  <span>{t.gradcamOverlay}</span>
                  <div className="xai-img-frame">
                    {heatmapUrl ? (
                      <img src={heatmapUrl} alt="Grad-CAM Saliency" />
                    ) : (
                      <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                        <p>📡 {t.gradcamOfflineNote || 'Grad-CAM computed on cloud sync.'}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Interactive Opacity Slider View */}
            {comparisonMode === 'slider' && heatmapUrl && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div
                  style={{
                    position: 'relative',
                    width: '100%',
                    aspectRatio: '1',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: 'var(--bg-secondary)'
                  }}
                >
                  <img
                    src={leafUrl}
                    alt="Original Leaf"
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                  />
                  <img
                    src={heatmapUrl}
                    alt="Grad-CAM Overlay"
                    style={{
                      position: 'absolute',
                      inset: 0,
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                      opacity: overlayOpacity / 100,
                      mixBlendMode: 'multiply',
                      transition: 'opacity 0.05s ease'
                    }}
                  />
                  <div
                    style={{
                      position: 'absolute',
                      bottom: '8px',
                      left: '8px',
                      background: 'rgba(0,0,0,0.65)',
                      color: '#ffffff',
                      fontSize: '0.7rem',
                      padding: '0.15rem 0.45rem',
                      borderRadius: '4px',
                      fontWeight: 600
                    }}
                  >
                    Overlay: {overlayOpacity}%
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.35rem 0.5rem', background: 'var(--bg-secondary)', borderRadius: '6px' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Leaf Only (0%)</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={overlayOpacity}
                    onChange={(e) => setOverlayOpacity(parseInt(e.target.value))}
                    style={{ flex: 1, accentColor: 'var(--accent-terracotta)', cursor: 'pointer' }}
                  />
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Full CAM (100%)</span>
                </div>
              </div>
            )}

            {/* Scientific Explanation Callout */}
            <div style={{ background: 'var(--bg-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontSize: '0.8125rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                <Info size={15} color="var(--accent-terracotta)" />
                <span>Convolutional Saliency & Attention Map</span>
              </div>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.5, fontSize: '0.78rem' }}>
                {lang === 'mr'
                  ? 'Grad-CAM हे मॉडेलच्या शेवटच्या कन्व्होल्युशनल लेयरमधील ग्रेडियंट्स टॅप करून पानावर कोणत्या रोगाचे लक्षण दिसून आले ते लाल/पिवळ्या रंगाने दर्शवते. हे रोग निदान थेट प्रमाणित करते.'
                  : 'Positive gradients are pooled from the final convolutional stage (features[16] in MobileNetV3 / features[8] in EfficientNet-B0) to generate a class activation heatmap. Warm colors (red/orange) pinpoint the exact foliar lesions driving the neural classification.'}
              </p>
            </div>

            {/* Top Classifications Bar if Edge Inference */}
            {diagResult.top_predictions?.length > 1 && (
              <div style={{ background: 'var(--bg-card)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <h5 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.4rem' }}>
                  Top Pathology Probabilities:
                </h5>
                {diagResult.top_predictions.slice(0, 3).map((p, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', padding: '0.2rem 0' }}>
                    <span>{p.disease}</span>
                    <strong>{p.confidence_percentage}%</strong>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: Actionable Agronomic Advisory */}
        {activeTab === 'advisory' && (
          <div className="advisory-block">
            {/* Three-Tier Confidence Policy Indicator (SRS FR-015, AIQ-005) */}
            {diagResult.confidence >= 0.75 ? (
              <div style={{ background: 'var(--status-optimal-bg)', border: '1px solid var(--status-optimal-border)', color: 'var(--status-optimal-text)', padding: '0.65rem 0.85rem', borderRadius: '8px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle2 size={16} />
                <div>
                  <strong>Tier 1: High Diagnostic Grounding (Confidence: {confidencePct}%)</strong>
                  <div>Full CIBRC-registered therapeutic prescriptions and Pre-Harvest Intervals verified.</div>
                </div>
              </div>
            ) : diagResult.confidence >= 0.50 ? (
              <div style={{ background: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)', color: 'var(--status-warning-text)', padding: '0.65rem 0.85rem', borderRadius: '8px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={16} />
                <div>
                  <strong>Tier 2: Moderate Diagnostic Grounding (Confidence: {confidencePct}%)</strong>
                  <div>Chemical interventions strictly suppressed under regulatory safety policy. Cultural sanitation only.</div>
                </div>
              </div>
            ) : (
              <div style={{ background: 'var(--status-danger-bg)', border: '1px solid var(--status-danger-border)', color: 'var(--status-danger-text)', padding: '0.65rem 0.85rem', borderRadius: '8px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldAlert size={16} />
                <div>
                  <strong>Tier 3: Inconclusive Classification (Confidence: {confidencePct}%)</strong>
                  <div>All chemical and therapeutic advice suppressed. Immediate referral to KVK agronomist recommended.</div>
                </div>
              </div>
            )}

            {/* Disease Overview */}
            <div style={{ background: 'var(--bg-secondary)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontSize: '0.8125rem' }}>
              <h5 style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                📖 {lang === 'mr' ? 'रोगाची माहिती' : 'Pathology Overview'}
              </h5>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {advisory.disease_overview?.[lang] || advisory.disease_overview?.en || 'Grounded agronomic advisory curated from ICAR & CIBRC packages of practices.'}
              </p>
            </div>

            {/* Cultural Practices (Always Shown) */}
            {advisory.cultural_practices?.length > 0 && (
              <div style={{ background: 'var(--bg-card)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <h5 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-green)', marginBottom: '0.4rem' }}>
                  🌱 {t.culturalMethods}
                </h5>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  {advisory.cultural_practices.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* CIBRC Chemical Prescriptions (Gated to Tier 1 >= 75%) */}
            {diagResult.confidence >= 0.75 ? (
              advisory.chemical_prescriptions?.map((chem, idx) => (
                <div key={idx} className="prescription-item-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h5>🧪 {chem.chemical_name}</h5>
                    {chem.phi_days && (
                      <span style={{ fontSize: '0.7rem', background: 'var(--status-warning-bg)', color: 'var(--status-warning-text)', padding: '0.15rem 0.4rem', borderRadius: '4px', fontWeight: 600 }}>
                        PHI: {chem.phi_days} Days
                      </span>
                    )}
                  </div>
                  <div className="prescription-meta">
                    <div><strong>Dose:</strong> {chem.dosage} ({chem.dilution})</div>
                    <div><strong>Method:</strong> {chem.application_method}</div>
                  </div>
                </div>
              ))
            ) : (
              <div style={{ background: '#FFFBEB', border: '1px dashed #F59E0B', borderRadius: '8px', padding: '0.85rem', fontSize: '0.78rem', color: '#B45309' }}>
                <strong>🔒 Chemical Prescriptions Suppressed:</strong>{' '}
                {lang === 'mr'
                  ? 'रोग निदान अचूकता ७५% पेक्षा कमी असल्याने कीटकनाशक कायद्यानुसार रासायनिक औषधांची नावे लपवली आहेत. कृपया वरील जैविक/मशागत उपाय करा किंवा KVK तज्ज्ञांची मदत घ्या.'
                  : 'Under regulatory agronomic safety rules, chemical recommendations are locked when visual certainty is below 75% to prevent inappropriate fungicide application.'}
                <div style={{ marginTop: '0.5rem' }}>
                  <button
                    onClick={onOpenKvkModal}
                    style={{
                      background: '#B45309',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '4px',
                      padding: '0.35rem 0.65rem',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    🏛️ {lang === 'mr' ? 'KVK तज्ज्ञांकडे पाठवा' : 'Request KVK Second Opinion'}
                  </button>
                </div>
              </div>
            )}

            {/* Statutory Legal Disclaimer */}
            <div className="statutory-callout">
              <strong>⚖️ Statutory Notice under Insecticides Act, 1968:</strong>{' '}
              {advisory.statutory_disclaimer?.[lang] || advisory.statutory_disclaimer?.en ||
                'Chemical dosages are synthesized strictly from published CIBRC and ICAR packages of practices. Verify application against the container label.'}
            </div>
          </div>
        )}

        {/* TAB 3: Microclimate & Spray Window Gating */}
        {activeTab === 'weather' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Spray Window Status Box */}
            <div
              style={{
                padding: '1rem',
                borderRadius: '8px',
                border: '1px solid',
                backgroundColor:
                  sprayWindow.status === 'optimal'
                    ? 'var(--status-optimal-bg)'
                    : sprayWindow.status === 'cancelled'
                    ? 'var(--status-danger-bg)'
                    : 'var(--status-warning-bg)',
                borderColor:
                  sprayWindow.status === 'optimal'
                    ? 'var(--status-optimal-border)'
                    : sprayWindow.status === 'cancelled'
                    ? 'var(--status-danger-border)'
                    : 'var(--status-warning-border)',
                color:
                  sprayWindow.status === 'optimal'
                    ? 'var(--status-optimal-text)'
                    : sprayWindow.status === 'cancelled'
                    ? 'var(--status-danger-text)'
                    : 'var(--status-warning-text)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: '0.95rem' }}>
                <span>
                  {sprayWindow.status === 'optimal'
                    ? '✅ ' + t.optimalSpray
                    : sprayWindow.status === 'cancelled'
                    ? '❌ ' + t.cancelledSpray
                    : '⚠️ ' + t.postponedSpray}
                </span>
                <span>Delta-T: {sprayWindow.delta_t_c ? sprayWindow.delta_t_c.toFixed(1) : '--'}°C</span>
              </div>
              <p style={{ marginTop: '0.35rem', fontSize: '0.8rem', lineHeight: 1.4 }}>
                {sprayWindow.reason || sprayWindow.advisory_message || 'Atmospheric conditions evaluated via Open-Meteo microclimate engine.'}
              </p>
            </div>

            {/* Telemetry Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
              <div style={{ background: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Temperature</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>{weatherData?.current?.temperature_c ?? '--'}°C</div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Relative Humidity</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>{weatherData?.current?.relative_humidity_pct ?? '--'}%</div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Wind Speed</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>{weatherData?.current?.wind_speed_kmh ?? '--'} km/h</div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '8px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Rain Probability</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>{weatherData?.current?.precipitation_probability_6h ?? '0'}%</div>
              </div>
            </div>

            {/* Multimodal Composite Health Index */}
            {multimodal.crop_health_index !== undefined && (
              <div style={{ background: 'var(--bg-card)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>Composite Crop Health Index</span>
                  <span style={{ fontSize: '1.1rem', fontWeight: 700, color: multimodal.crop_health_index >= 70 ? 'var(--accent-green)' : 'var(--accent-terracotta)' }}>
                    {multimodal.crop_health_index.toFixed(1)} / 100
                  </span>
                </div>
                <div style={{ marginTop: '0.35rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Infection Velocity: <strong>{multimodal.disease_progression_velocity || 'MODERATE'}</strong>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: KVK Agronomist Escalation */}
        {activeTab === 'kvk' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ background: 'var(--bg-secondary)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🏛️</div>
              <h4 style={{ color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                {lang === 'mr' ? 'कृषी विज्ञान केंद्र (KVK) तज्ज्ञ मार्गदर्शन' : 'Krishi Vigyan Kendra (KVK) Escalation'}
              </h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '1rem' }}>
                {lang === 'mr'
                  ? 'जर AI रोग निदानाबद्दल शंका असेल किंवा रोगाची तीव्रता जास्त असेल, तर हा अहवाल थेट आपल्या तालुक्यातील KVK तज्ज्ञांकडे अधिकृत पडताळणीसाठी पाठवा.'
                  : 'If the diagnosis confidence is moderate/uncertain, or symptoms appear atypical, submit this complete case history and Grad-CAM evidence to local Taluka Agricultural Officers or KVK pathologists.'}
              </p>
              <button
                className="topbar-btn"
                onClick={onOpenKvkModal}
                style={{
                  margin: '0 auto',
                  background: 'var(--accent-terracotta)',
                  color: '#ffffff',
                  fontWeight: 600,
                  padding: '0.6rem 1.25rem',
                  borderColor: 'transparent'
                }}
              >
                <UserCheck size={16} />
                <span>{lang === 'mr' ? 'KVK तज्ज्ञांकडे पाठवा' : 'Escalate Case to KVK'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
