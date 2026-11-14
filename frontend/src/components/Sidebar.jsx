import React from 'react';
import {
  Plus,
  PanelLeftClose,
  PanelLeft,
  Sprout,
  History,
  Trash2,
  Download,
  Wifi,
  WifiOff,
  Database,
  MapPin,
  FileText
} from 'lucide-react';

export default function Sidebar({
  isOpen,
  onToggle,
  lang,
  onLangChange,
  t,
  isOnline,
  queueStats,
  onManualSync,
  isSyncing,
  farms,
  activeFarmId,
  onSelectFarm,
  onOpenFarmModal,
  historyList,
  onSelectHistory,
  onDeleteHistory,
  onExportHistory,
  onNewAnalysis,
  onOpenOfflineGuide,
  storageInfo,
  onPreloadModel,
  modelCachedMap,
  cachingCrop,
  profile,
  onOpenProfile,
  onCloseMobile
}) {
  const handleItemClick = (callback) => {
    return (e) => {
      if (callback) callback(e);
      if (onCloseMobile) onCloseMobile();
    };
  };

  return (
    <aside className={`claude-sidebar ${isOpen ? '' : 'collapsed'}`}>
      {/* Sidebar Header */}
      <div className="sidebar-header">
        <a href="#" className="brand-link" onClick={(e) => { e.preventDefault(); onNewAnalysis(); if (onCloseMobile) onCloseMobile(); }}>
          <div className="brand-leaf-icon">
            <Sprout size={18} />
          </div>
          <div className="brand-title-wrap">
            <h1>PikVaidya AI</h1>
            <span>{lang === 'mr' ? 'पीकवैद्य कृषी मित्र' : lang === 'hi' ? 'पीकवैद्य कृषि मित्र' : 'Agronomic Assistant'}</span>
          </div>
        </a>
        <button
          className="sidebar-toggle-btn"
          onClick={onToggle}
          title={isOpen ? "Collapse Sidebar" : "Expand Sidebar"}
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      {/* "+ Start New Diagnosis" Action Button */}
      <button className="new-chat-btn" onClick={() => { onNewAnalysis(); if (onCloseMobile) onCloseMobile(); }}>
        <div className="new-chat-left">
          <Plus size={16} />
          <span>{lang === 'mr' ? 'नवीन पीक रोग तपासणी' : lang === 'hi' ? 'नई फसल रोग जांच' : 'New Leaf Diagnosis'}</span>
        </div>
        <span className="shortcut-badge desktop-only">⌘N</span>
      </button>

      {/* Scrollable Sidebar Body */}
      <div className="sidebar-body">
        {/* Farm & Plots Context Section (SRS FR-005 to FR-008) */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 0.5rem 0.35rem 0.5rem' }}>
            <span className="sidebar-section-title" style={{ padding: 0 }}>
              {lang === 'mr' ? 'माझी शेती / भूखंड' : lang === 'hi' ? 'मेरे खेत / प्लाॅट' : 'My Farm Plots'}
            </span>
            <button
              onClick={() => { onOpenFarmModal(); if (onCloseMobile) onCloseMobile(); }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-terracotta)',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.2rem'
              }}
              title="Add or configure plots"
            >
              <Plus size={13} /> {lang === 'mr' ? 'जोडा' : 'Add'}
            </button>
          </div>

          <div className="farm-plots-list">
            {farms.map((plot) => (
              <button
                key={plot.id}
                className={`farm-plot-item ${activeFarmId === plot.id ? 'active' : ''}`}
                onClick={() => { onSelectFarm(plot.id); if (onCloseMobile) onCloseMobile(); }}
              >
                <div className="plot-name-wrap">
                  <span>{plot.crop === 'sugarcane' ? '🍬' : plot.crop === 'tomato' ? '🍅' : '🧅'}</span>
                  <span>{plot.name}</span>
                </div>
                <span className="plot-badge">{plot.area} Ac</span>
              </button>
            ))}
            {farms.length === 0 && (
              <div style={{ padding: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {lang === 'mr' ? 'अद्याप भूखंड जोडलेले नाहीत.' : 'No plots configured yet.'}
              </div>
            )}
          </div>
        </div>

        {/* Diagnosis History Group */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 0.5rem 0.35rem 0.5rem' }}>
            <span className="sidebar-section-title" style={{ padding: 0 }}>
              {lang === 'mr' ? 'निदान इतिहास' : lang === 'hi' ? 'निदान इतिहास' : 'Recent Diagnoses'}
            </span>
            {historyList.length > 0 && (
              <button
                onClick={onExportHistory}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '0.7rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.2rem'
                }}
                title="Export history backup (JSON)"
              >
                <Download size={12} /> JSON
              </button>
            )}
          </div>

          <div className="history-group">
            {historyList.slice(0, 15).map((item) => (
              <div
                key={item.diagnosis_id}
                style={{ display: 'flex', alignItems: 'center', position: 'relative' }}
              >
                <button
                  className="history-item-btn"
                  onClick={() => onSelectHistory(item)}
                >
                  <div className="history-left">
                    <img
                      src={item.image_reference || '/pwa-192x192.png'}
                      alt=""
                      className="history-thumb"
                    />
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <div style={{ fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                        {item.predicted_disease}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {item.farm_name ? <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>{item.farm_name} · </span> : ''}
                        {item.crop_type} · {(item.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onDeleteHistory(item.diagnosis_id); }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-light)',
                    cursor: 'pointer',
                    padding: '0.3rem',
                    position: 'absolute',
                    right: '4px'
                  }}
                  title="Delete record"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}

            {historyList.length === 0 && (
              <div style={{ padding: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {t.noOfflineHistory}
              </div>
            )}
          </div>
        </div>

        {/* Offline Agricultural Guide Trigger */}
        <div>
          <button
            className="topbar-btn"
            style={{ width: '100%', justifyContent: 'flex-start', padding: '0.6rem 0.75rem' }}
            onClick={() => { onOpenOfflineGuide(); if (onCloseMobile) onCloseMobile(); }}
          >
            <FileText size={15} />
            <span>{t.offlineGuideTitle}</span>
          </button>
        </div>

        {/* Pre-load Edge Models Chip */}
        <div style={{ background: 'var(--bg-card)', padding: '0.65rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontSize: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>⚡ Edge WASM AI</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Offline</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginBottom: '0.5rem' }}>
            {lang === 'mr' ? 'इंटरनेट नसताना तपासणीसाठी मॉडेल्स डाऊनलोड करा:' : 'Pre-download models for zero-internet field diagnosis:'}
          </p>
          <div style={{ display: 'flex', gap: '0.3rem' }}>
            {['sugarcane', 'tomato', 'onion'].map((c) => (
              <button
                key={c}
                onClick={() => onPreloadModel(c)}
                disabled={modelCachedMap[c] || cachingCrop === c || !isOnline}
                style={{
                  flex: 1,
                  padding: '0.25rem',
                  fontSize: '0.7rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border-subtle)',
                  background: modelCachedMap[c] ? 'var(--status-optimal-bg)' : 'var(--bg-secondary)',
                  color: modelCachedMap[c] ? 'var(--status-optimal-text)' : 'var(--text-secondary)',
                  cursor: modelCachedMap[c] ? 'default' : 'pointer'
                }}
              >
                {cachingCrop === c ? '⏳' : modelCachedMap[c] ? '✓ ' + c.slice(0, 3) : '+ ' + c.slice(0, 3)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Sidebar Footer */}
      <div className="sidebar-footer">
        {/* Farmer Profile Mini Bar (SRS FR-001 - FR-004) */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.45rem 0.6rem',
            background: 'var(--bg-card)',
            borderRadius: '8px',
            border: '1px solid var(--border-subtle)',
            cursor: 'pointer'
          }}
          onClick={() => { onOpenProfile(); if (onCloseMobile) onCloseMobile(); }}
          title="Edit Farmer Profile & Consent (FR-004, FR-007)"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--accent-terracotta-light)', color: 'var(--accent-terracotta)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 700 }}>
              {profile?.name ? profile.name.slice(0, 1).toUpperCase() : 'R'}
            </div>
            <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '160px' }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.1 }}>
                {profile?.name || 'Ramesh Patil'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                {profile?.district?.toUpperCase() || 'PUNE'} · Farmer
              </div>
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>⚙️</span>
        </div>

        <div className="sidebar-status-row">
          <div className={`status-pill ${isOnline ? 'online' : 'offline'}`}>
            {isOnline ? <Wifi size={12} /> : <WifiOff size={12} />}
            <span>{isOnline ? t.onlineStatus : t.offlineStatus}</span>
          </div>

          {queueStats.pendingCount > 0 && (
            <button
              onClick={onManualSync}
              disabled={isSyncing || !isOnline}
              style={{
                background: 'var(--accent-terracotta-light)',
                border: 'none',
                color: 'var(--accent-terracotta)',
                fontSize: '0.75rem',
                fontWeight: 600,
                borderRadius: '9999px',
                padding: '0.2rem 0.5rem',
                cursor: 'pointer'
              }}
            >
              🔄 {queueStats.pendingCount}
            </button>
          )}

          {/* Trilingual Language Selector */}
          <div className="lang-selector-mini">
            <button
              className={`lang-tab ${lang === 'mr' ? 'active' : ''}`}
              onClick={() => onLangChange('mr')}
            >
              मरा
            </button>
            <button
              className={`lang-tab ${lang === 'hi' ? 'active' : ''}`}
              onClick={() => onLangChange('hi')}
            >
              हिं
            </button>
            <button
              className={`lang-tab ${lang === 'en' ? 'active' : ''}`}
              onClick={() => onLangChange('en')}
            >
              EN
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-light)' }}>
          <span>Storage: {storageInfo.usageMB} MB</span>
          <span>PikVaidya v1.3.0</span>
        </div>
      </div>
    </aside>
  );
}

