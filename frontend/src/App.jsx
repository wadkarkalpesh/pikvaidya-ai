import React, { useState, useEffect, useRef } from 'react';
import { translations } from './i18n/translations';
import { syncManager } from './offline/syncManager';
import {
  openDB,
  saveDiagnosis,
  getAllDiagnoses,
  deleteDiagnosis,
  getSyncQueueStats,
  getStorageEstimate,
  exportDatabaseToJson,
  queueOfflineDiagnosis,
  searchOfflineKnowledge
} from './offline/db';
import {
  runLocalEdgeInference,
  isModelCached,
  cacheModelForOffline
} from './offline/edgeInference';

export default function App() {
  const [lang, setLang] = useState('mr'); // Default Marathi for regional farmers
  const [crop, setCrop] = useState('sugarcane');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [edgeLoading, setEdgeLoading] = useState(false);
  const [diagResult, setDiagResult] = useState(null);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [weatherData, setWeatherData] = useState(null);
  const [district, setDistrict] = useState('pune');
  const [districtsList, setDistrictsList] = useState([]);
  const [gpsLocation, setGpsLocation] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [forecastTab, setForecastTab] = useState('hourly'); // 'hourly' | 'daily'

  // Offline-First & Network State
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [queueStats, setQueueStats] = useState({ pendingCount: 0, failedCount: 0, totalQueued: 0 });
  const [isSyncing, setIsSyncing] = useState(false);
  const [offlineBanner, setOfflineBanner] = useState(null);
  const [showOfflineModal, setShowOfflineModal] = useState(false);
  const [offlineSearch, setOfflineSearch] = useState('');
  const [offlineChunks, setOfflineChunks] = useState([]);

  // PWA Install Prompt
  const [deferredPrompt, setDeferredPrompt] = useState(null);

  // Model Caching & Edge AI State
  const [modelCachedMap, setModelCachedMap] = useState({ sugarcane: false, tomato: false, onion: false });
  const [cachingCrop, setCachingCrop] = useState(null);

  // Diagnosis History Modal & Storage State
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyList, setHistoryList] = useState([]);
  const [storageInfo, setStorageInfo] = useState({ usageMB: '0.00', quotaMB: '0.00', percentUsed: 0 });

  // RAG Chatbot state
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const chatBottomRef = useRef(null);

  const t = translations[lang] || translations.en;

  // Refresh Queue Stats helper
  const refreshQueue = async () => {
    try {
      const stats = await getSyncQueueStats();
      setQueueStats(stats);
    } catch (e) {
      console.warn('Could not read offline queue stats:', e);
    }
  };

  const refreshStorage = async () => {
    try {
      const est = await getStorageEstimate();
      setStorageInfo(est);
    } catch (e) {
      console.warn('Could not read storage estimate:', e);
    }
  };

  const checkModelCaches = async () => {
    try {
      const [sc, tm, on] = await Promise.all([
        isModelCached('sugarcane'),
        isModelCached('tomato'),
        isModelCached('onion')
      ]);
      setModelCachedMap({ sugarcane: sc, tomato: tm, onion: on });
    } catch (e) {
      console.warn('Could not check model cache:', e);
    }
  };

  // PWA beforeinstallprompt handler
  useEffect(() => {
    const handleBeforeInstall = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };
    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      setDeferredPrompt(null);
    }
  };

  // Subscribe to network & sync state
  useEffect(() => {
    const unsubNet = syncManager.addNetworkListener((online) => {
      setIsOnline(online);
      refreshQueue();
    });

    const unsubSync = syncManager.addSyncListener((res) => {
      refreshQueue();
      if (res.syncedCount > 0) {
        setOfflineBanner(`✅ ${res.syncedCount} offline scans synchronized successfully!`);
      }
    });

    refreshQueue();
    refreshStorage();
    checkModelCaches();

    // Pre-cache knowledge chunks when online
    if (typeof navigator !== 'undefined' && navigator.onLine) {
      syncManager.refreshOfflineCaches();
    }

    return () => {
      unsubNet();
      unsubSync();
    };
  }, []);

  // Check model cache whenever crop changes
  useEffect(() => {
    checkModelCaches();
  }, [crop]);

  // Initial welcome message for chat
  useEffect(() => {
    const welcomeText = lang === 'mr'
      ? "नमस्कार! मी पिकवैद्य AI कृषी मित्र आहे. ऊस, टोमॅटो व कांदा पिकांवरील रोग, औषधांची मात्रा (ICAR/CIBRC) किंवा हवामान फवारणीबद्दल विचारा."
      : lang === 'hi'
      ? "नमस्ते! मैं पिकवैद्य AI कृषि सहायक हूं। गन्ना, टमाटर और प्याज की बीमारियों, कीटनाशक की मात्रा या मौसम अनुकूलता के बारे में पूछें।"
      : "Hello! I am PikVaidya AI Agricultural Assistant. Ask me anything about sugarcane, tomato, and onion pathology, ICAR/CIBRC chemical dosages, or weather spray suitability.";

    setChatMessages([
      { sender: 'bot', text: welcomeText, sources: [] }
    ]);
  }, [lang]);

  // Fetch Maharashtra districts on load
  useEffect(() => {
    async function fetchDistricts() {
      try {
        const res = await fetch('/api/v1/weather/locations');
        if (res.ok) {
          const data = await res.json();
          setDistrictsList(data.locations || []);
        }
      } catch (err) {
        console.warn('Could not load districts:', err);
      }
    }
    fetchDistricts();
  }, []);

  // Fetch weather telemetry whenever district or GPS changes
  useEffect(() => {
    async function fetchWeather() {
      setWeatherLoading(true);
      try {
        let url = `/api/v1/weather/current?district=${encodeURIComponent(district)}`;
        if (gpsLocation?.lat && gpsLocation?.lon) {
          url = `/api/v1/weather/current?latitude=${gpsLocation.lat}&longitude=${gpsLocation.lon}`;
        }
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setWeatherData(data);
        }
      } catch (err) {
        console.warn('Weather fetch failed (possibly offline):', err);
      } finally {
        setWeatherLoading(false);
      }
    }
    fetchWeather();
  }, [district, gpsLocation]);

  // Handle GPS location acquisition
  const handleUseGps = () => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setGpsLocation({
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
          });
        },
        (err) => {
          alert('GPS error: ' + err.message);
        }
      );
    } else {
      alert('Geolocation is not supported by your browser.');
    }
  };

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      setImagePreview(URL.createObjectURL(file));
      setDiagResult(null);
    }
  };

  const handleManualSync = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    await syncManager.syncNow();
    await refreshQueue();
    setIsSyncing(false);
  };

  // Model download for offline cache
  const handleCacheModel = async (targetCrop) => {
    try {
      setCachingCrop(targetCrop);
      await cacheModelForOffline(targetCrop);
      setModelCachedMap(prev => ({ ...prev, [targetCrop]: true }));
      setOfflineBanner(`✅ ${targetCrop.toUpperCase()} model downloaded and cached for offline use.`);
      refreshStorage();
    } catch (err) {
      alert(`Failed to cache model: ${err.message}`);
    } finally {
      setCachingCrop(null);
    }
  };

  // Open Diagnosis History Modal
  const handleOpenHistory = async () => {
    const list = await getAllDiagnoses({ limit: 50 });
    setHistoryList(list);
    setShowHistoryModal(true);
    refreshStorage();
  };

  const handleDeleteHistory = async (diagId, e) => {
    e.stopPropagation();
    if (confirm('Delete this saved diagnostic record?')) {
      await deleteDiagnosis(diagId);
      const updated = await getAllDiagnoses({ limit: 50 });
      setHistoryList(updated);
      refreshStorage();
    }
  };

  const handleExportHistory = async () => {
    const jsonStr = await exportDatabaseToJson();
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pikvaidya_offline_backup_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSelectHistoryItem = (item) => {
    setImagePreview(item.image_reference);
    setDiagResult({
      crop: item.crop_type,
      crop_detection_method: item.is_local_inference ? 'edge_onnx_wasm_int8' : 'cloud_pytorch',
      predicted_class: item.predicted_disease,
      disease_name_multilingual: { en: item.predicted_disease, mr: item.predicted_disease, hi: item.predicted_disease },
      confidence: item.confidence,
      confidence_percentage: Math.round(item.confidence * 1000) / 10,
      heatmap_path: item.gradcam_reference,
      is_local_inference: item.is_local_inference,
      inference_time_ms: null,
      top_predictions: [],
      gradcam_notice: item.is_local_inference && !item.gradcam_reference
        ? t.gradcamOfflineNote
        : null,
      model_version: item.is_local_inference ? 'MobileNetV3 INT8 Edge WASM' : 'PikVaidya Cloud PyTorch',
      details: {
        severity: item.risk_level || 'ANALYZED',
        offline_queued: item.sync_status === 'pending_sync'
      },
      recommendations: {
        cultural: item.recommendations?.length > 0 ? [item.recommendations[0]] : [],
        chemical: item.recommendations?.length > 1 ? item.recommendations.slice(1) : []
      }
    });
    setShowHistoryModal(false);
  };

  // Client-Side Edge AI Inference (WASM INT8)
  const handleEdgeDiagnose = async () => {
    if (!selectedImage && !imagePreview) return;
    setEdgeLoading(true);

    try {
      const targetCrop = crop === 'auto' ? 'sugarcane' : crop;
      const edgeResult = await runLocalEdgeInference(targetCrop, imagePreview);

      // Save into diagnosis_history and sync_queue
      await queueOfflineDiagnosis({
        image_data: imagePreview,
        image_name: selectedImage ? selectedImage.name : 'edge_capture.jpg',
        crop: targetCrop,
        district: district,
        latitude: gpsLocation?.lat || null,
        longitude: gpsLocation?.lon || null,
        captured_at: new Date().toISOString(),
        client_preview: edgeResult,
        is_local_inference: true
      });

      await refreshQueue();
      await refreshStorage();

      setDiagResult({
        crop: targetCrop,
        crop_detection_method: 'edge_onnx_wasm_int8',
        predicted_class: edgeResult.predicted_disease,
        disease_name_multilingual: {
          en: edgeResult.predicted_disease,
          mr: edgeResult.predicted_disease,
          hi: edgeResult.predicted_disease
        },
        confidence: edgeResult.confidence,
        confidence_percentage: edgeResult.confidence_percentage,
        heatmap_path: null,
        is_local_inference: true,
        inference_time_ms: edgeResult.inference_time_ms,
        top_predictions: edgeResult.top_predictions,
        gradcam_notice: edgeResult.gradcam_notice,
        model_version: `MobileNetV3 INT8 Edge WASM (${edgeResult.inference_time_ms}ms)`,
        details: {
          severity: 'ON_DEVICE_ANALYSIS',
          offline_queued: true
        },
        recommendations: {
          cultural: edgeResult.recommendations.slice(0, 1),
          chemical: edgeResult.recommendations.slice(1)
        }
      });

      setOfflineBanner(`⚡ Local diagnosis complete in ${edgeResult.inference_time_ms}ms! Saved to offline history.`);
    } catch (err) {
      alert(`Edge AI inference failed: ${err.message}. If the model is not cached, please connect to internet to download.`);
    } finally {
      setEdgeLoading(false);
    }
  };

  // Cloud / Primary Server Diagnosis (with Grad-CAM)
  const handleDiagnose = async () => {
    if (!selectedImage) return;
    setLoading(true);

    // If browser is offline, automatically redirect to Edge AI inference!
    if (typeof navigator !== 'undefined' && (!navigator.onLine || !isOnline)) {
      setLoading(false);
      await handleEdgeDiagnose();
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', selectedImage);
      formData.append('crop_type', crop);
      formData.append('crop', crop);
      formData.append('generate_gradcam', 'true');
      formData.append('save_heatmap', 'true');
      if (gpsLocation?.lat && gpsLocation?.lon) {
        formData.append('latitude', gpsLocation.lat);
        formData.append('longitude', gpsLocation.lon);
      } else if (district) {
        formData.append('district', district);
      }

      // Call the Unified Multi-Crop Prediction Endpoint
      let response = await fetch('/api/crop-health/predict', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        response = await fetch('/api/v1/diagnose', {
          method: 'POST',
          body: formData,
        });
      }

      if (!response.ok) {
        throw new Error(`Diagnosis failed: HTTP ${response.status}`);
      }

      const data = await response.json();
      setDiagResult(data);

      // Save to local IndexedDB history
      await saveDiagnosis({
        crop_type: data.crop || crop,
        predicted_disease: data.predicted_class,
        confidence: data.confidence,
        image_reference: imagePreview,
        gradcam_reference: data.heatmap_path,
        latitude: gpsLocation?.lat || null,
        longitude: gpsLocation?.lon || null,
        diagnosis_timestamp: new Date().toISOString(),
        sync_status: 'synced',
        is_local_inference: false,
        recommendations: data.details?.contextual_advisory?.cultural_practices || []
      });

      await refreshStorage();
    } catch (err) {
      alert('Diagnostic Error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!diagResult) return;
    setPdfDownloading(true);

    try {
      const payload = {
        crop: diagResult.crop || crop,
        disease_name: diagResult.predicted_class,
        confidence: diagResult.confidence,
        severity: diagResult.details?.severity || "MODERATE",
        language: lang,
        district: district,
        latitude: gpsLocation?.lat || null,
        longitude: gpsLocation?.lon || null,
        image_path: diagResult.image_path || null,
        heatmap_path: diagResult.heatmap_path || null,
        contextual_advisory: diagResult.details?.contextual_advisory || null,
        weather_telemetry: weatherData?.current || null,
        spray_window: weatherData?.spray_window || null
      };

      const res = await fetch('/api/v1/advisory/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('PDF generation failed');

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `PikVaidya_Advisory_${diagResult.crop}_${diagResult.predicted_class.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('PDF generation error: ' + err.message);
    } finally {
      setPdfDownloading(false);
    }
  };

  const handleSendMessage = async (customText = null) => {
    const textToSend = customText || chatInput;
    if (!textToSend.trim() || chatLoading) return;

    const userMsg = { sender: 'user', text: textToSend };
    setChatMessages(prev => [...prev, userMsg]);
    if (!customText) setChatInput('');
    setChatLoading(true);

    // If offline, search client-side IndexedDB knowledge base directly
    if (typeof navigator !== 'undefined' && (!navigator.onLine || !isOnline)) {
      try {
        const localChunks = await searchOfflineKnowledge(crop !== 'auto' ? crop : null, textToSend, lang);
        if (localChunks.length > 0) {
          const reply = lang === 'mr'
            ? `[ऑफलाइन माहिती] ${localChunks[0].text}`
            : `[Offline Knowledge] ${localChunks[0].text}`;
          setChatMessages(prev => [
            ...prev,
            { sender: 'bot', text: reply, sources: localChunks.map(c => ({ source_name: c.source || 'ICAR' })) }
          ]);
        } else {
          setChatMessages(prev => [
            ...prev,
            {
              sender: 'bot',
              text: lang === 'mr'
                ? "ऑफलाइन उपलब्ध माहितीमध्ये उत्तर सापडले नाही. इंटरनेट जोडणी झाल्यावर पूर्ण RAG उत्तरे मिळतील."
                : "No matching offline information found. Online connection required for complete RAG AI assistant."
            }
          ]);
        }
      } catch (err) {
        setChatMessages(prev => [
          ...prev,
          { sender: 'bot', text: `Offline search error: ${err.message}` }
        ]);
      } finally {
        setChatLoading(false);
      }
      return;
    }

    try {
      const payload = {
        query: textToSend,
        language: lang,
        session_id: sessionId,
        crop_context: diagResult ? diagResult.crop : (crop !== 'auto' ? crop : null),
        disease_context: diagResult ? diagResult.predicted_class : null
      };

      const res = await fetch('/api/v1/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error('Assistant query failed');

      const data = await res.json();
      setSessionId(data.session_id);
      setChatMessages(prev => [
        ...prev,
        {
          sender: 'bot',
          text: data.reply || data.answer,
          sources: data.sources || data.retrieved_sources || [],
          recommendations: data.key_recommendations || []
        }
      ]);
    } catch (err) {
      setChatMessages(prev => [
        ...prev,
        { sender: 'bot', text: `Error: ${err.message}`, sources: [] }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const currentCropKey = crop === 'auto' ? 'sugarcane' : crop;
  const isCurrentModelCached = modelCachedMap[currentCropKey];

  return (
    <div className="app-container">
      {/* Navigation */}
      <nav className="navbar">
        <div className="navbar-container">
          <div className="brand">
            <div className="brand-icon">🌿</div>
            <div className="brand-text">
              <h1>{t.appTitle}</h1>
              <p>{t.appSubtitle}</p>
            </div>
          </div>

          <div className="nav-actions">
            {/* PWA Install Button (When prompt available) */}
            {deferredPrompt && (
              <button className="pwa-install-btn" onClick={handleInstallClick} title="Install PikVaidya Progressive Web App">
                📲 {t.installApp}
              </button>
            )}

            {/* Online / Offline Status Pill */}
            <div className={`network-pill ${isOnline ? 'online' : 'offline'}`}>
              {isOnline ? `🟢 ${t.onlineStatus}` : `🟠 ${t.offlineStatus}`}
            </div>

            {/* Offline Queue Badge & Sync Trigger */}
            {queueStats.pendingCount > 0 && (
              <button
                className="sync-btn"
                onClick={handleManualSync}
                disabled={isSyncing || !isOnline}
                title="Sync queued offline scans"
              >
                🔄 {queueStats.pendingCount} {isSyncing ? t.syncing : t.syncNow}
              </button>
            )}

            {/* History Modal Trigger */}
            <button
              className="offline-guide-btn"
              onClick={handleOpenHistory}
              title="View saved local and cloud diagnoses"
            >
              📋 {t.offlineHistoryTitle}
            </button>

            {/* Offline Agricultural Guide Modal Button */}
            <button
              className="offline-guide-btn"
              onClick={async () => {
                setShowOfflineModal(true);
                const initialChunks = await searchOfflineKnowledge(crop !== 'auto' ? crop : null, '', lang);
                setOfflineChunks(initialChunks);
              }}
              title="Browse offline pathology knowledge"
            >
              📖 {t.offlineGuideTitle}
            </button>

            <select
              className="lang-select"
              value={lang}
              onChange={(e) => setLang(e.target.value)}
            >
              <option value="mr">मराठी (Marathi)</option>
              <option value="en">English</option>
              <option value="hi">हिंदी (Hindi)</option>
            </select>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {/* Offline Notification Banner */}
        {offlineBanner && (
          <div className="offline-banner">
            <span>📡 {offlineBanner}</span>
            <button onClick={() => setOfflineBanner(null)}>✕</button>
          </div>
        )}

        {/* Hero Banner */}
        <section className="hero-card">
          <div className="hero-text">
            <h2>{t.appSubtitle}</h2>
            <p>
              {lang === 'mr'
                ? "कृत्रिम बुद्धिमत्ता (PyTorch EfficientNet-B0 / MobileNetV3 INT8 WASM) आणि सूक्ष्म हवामान माहितीचा वापर करून शेतकरी बांधवांना थेट अचूक, वैधानिक व सुरक्षित शेती सल्ला — अगदी इंटरनेट नसतानाही!"
                : "Combining on-device Edge AI (MobileNetV3 WASM INT8) with cloud PyTorch and microclimate telemetry to deliver grounded, explainable, and offline-resilient farming advisories."}
            </p>
          </div>
          <div className="hero-badges">
            <div className="hero-badge">⚡ Edge INT8 WASM (Offline)</div>
            <div className="hero-badge">🌦️ Open-Meteo Weather Gating</div>
            <div className="hero-badge">📜 ICAR & CIBRC Grounded</div>
          </div>
        </section>

        {/* Dashboard Grid */}
        <div className="dashboard-grid">
          {/* Left Column: Image Upload & Crop Switcher */}
          <div className="left-col">
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <span>🌾</span> {t.selectCrop}
                </h3>
              </div>

              {/* Crop Tabs */}
              <div className="crop-tabs">
                <button
                  className={`crop-tab ${crop === 'auto' ? 'active' : ''}`}
                  onClick={() => { setCrop('auto'); setDiagResult(null); }}
                  title="Automatically identify crop from leaf foliage"
                >
                  🤖 {t.autoDetect}
                </button>
                <button
                  className={`crop-tab ${crop === 'sugarcane' ? 'active' : ''}`}
                  onClick={() => { setCrop('sugarcane'); setDiagResult(null); }}
                >
                  🍬 {t.sugarcane}
                </button>
                <button
                  className={`crop-tab ${crop === 'tomato' ? 'active' : ''}`}
                  onClick={() => { setCrop('tomato'); setDiagResult(null); }}
                >
                  🍅 {t.tomato}
                </button>
                <button
                  className={`crop-tab ${crop === 'onion' ? 'active' : ''}`}
                  onClick={() => { setCrop('onion'); setDiagResult(null); }}
                >
                  🧅 {t.onion}
                </button>
              </div>

              {/* Model Offline Cache Chip */}
              {crop !== 'auto' && (
                <div className={`model-cache-chip ${isCurrentModelCached ? 'cached' : ''}`}>
                  <span>{isCurrentModelCached ? '⚡ ' + t.modelCached : '📦 ' + t.modelNotCached}</span>
                  {!isCurrentModelCached && (
                    <button
                      onClick={() => handleCacheModel(crop)}
                      disabled={cachingCrop === crop || !isOnline}
                      title="Download 11.8MB INT8 model for offline use"
                    >
                      {cachingCrop === crop ? '⏳ Downloading...' : '⬇️ ' + t.cacheModelAction}
                    </button>
                  )}
                </div>
              )}

              {/* Upload Dropzone */}
              <label className="dropzone">
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleImageChange}
                  style={{ display: 'none' }}
                />
                <div className="dropzone-icon">📷</div>
                <h4>{t.uploadTitle}</h4>
                <p>{t.uploadSubtitle}</p>
              </label>

              {/* Image Preview */}
              {imagePreview && (
                <div className="preview-container">
                  <img src={imagePreview} alt="Selected Leaf" className="preview-img" />
                </div>
              )}

              {/* Primary Action Button (Cloud PyTorch + Grad-CAM) */}
              <button
                className="btn-primary"
                onClick={handleDiagnose}
                disabled={!selectedImage || loading || edgeLoading}
              >
                {loading ? t.diagnosing : (!isOnline ? '⚡ ' + t.runEdgeDiagnose : t.diagnoseButton)}
              </button>

              {/* On-Device Edge Inference Button (Instant WASM) */}
              <button
                className="btn-edge-diagnose"
                onClick={handleEdgeDiagnose}
                disabled={!selectedImage || loading || edgeLoading}
                title="Runs dynamic INT8 quantized MobileNetV3 directly in the browser via WebAssembly"
              >
                {edgeLoading ? '⏳ Running On-Device WASM...' : '⚡ ' + t.runEdgeDiagnose}
              </button>
            </div>

            {/* Weather Microclimate Card */}
            <div className="card">
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 className="card-title">
                  <span>🌦️</span> {t.weatherTitle}
                </h3>
                {weatherLoading && <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>⏳ Loading...</span>}
              </div>

              {/* District & GPS Selector */}
              <div className="weather-location-bar">
                <select
                  className="location-select"
                  value={gpsLocation ? 'custom_gps' : district}
                  onChange={(e) => {
                    if (e.target.value !== 'custom_gps') {
                      setGpsLocation(null);
                      setDistrict(e.target.value);
                    }
                  }}
                >
                  {gpsLocation && <option value="custom_gps">📍 Farm GPS ({gpsLocation.lat.toFixed(2)}, {gpsLocation.lon.toFixed(2)})</option>}
                  {districtsList.map((d) => (
                    <option key={d.id} value={d.id}>
                      {lang === 'mr' ? d.name_mr : lang === 'hi' ? d.name_hi : d.name} (Maharashtra)
                    </option>
                  ))}
                  {districtsList.length === 0 && (
                    <>
                      <option value="pune">Pune</option>
                      <option value="kolhapur">Kolhapur</option>
                      <option value="nashik">Nashik</option>
                      <option value="sangli">Sangli</option>
                    </>
                  )}
                </select>
                <button
                  className={`gps-btn ${gpsLocation ? 'active' : ''}`}
                  onClick={handleUseGps}
                  title="Detect GPS location"
                >
                  📍 {t.useGps}
                </button>
              </div>

              {weatherData && (
                <>
                  {/* Weather Alerts if any */}
                  {weatherData.alerts && weatherData.alerts.length > 0 && (
                    <div className="weather-alerts-container">
                      {weatherData.alerts.map((alt, idx) => (
                        <div key={idx} className={`weather-alert-card ${alt.severity}`}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                            <span>⚠️ {lang === 'mr' ? alt.title_mr || alt.title : lang === 'hi' ? alt.title_hi || alt.title : alt.title}</span>
                            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase' }}>{alt.severity}</span>
                          </div>
                          <p style={{ margin: 0, fontSize: '0.75rem' }}>
                            {lang === 'mr' ? alt.description_mr || alt.description : lang === 'hi' ? alt.description_hi || alt.description : alt.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Spray Window Status Pill */}
                  {weatherData.spray_window && (
                    <div className={`weather-status-box ${weatherData.spray_window.status || 'optimal'}`}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong>
                          {weatherData.spray_window.status === 'optimal'
                            ? `✅ ${t.optimalSpray}`
                            : weatherData.spray_window.status === 'cancelled'
                            ? `❌ ${t.cancelledSpray}`
                            : `⚠️ ${t.postponedSpray}`}
                        </strong>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>
                          Delta-T: {weatherData.spray_window.delta_t_c ? weatherData.spray_window.delta_t_c.toFixed(1) : '--'}°C
                        </span>
                      </div>
                      <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.8rem' }}>
                        {weatherData.spray_window.reason || weatherData.spray_window.advisory_message}
                      </p>
                    </div>
                  )}

                  {/* 6-Grid Telemetry */}
                  <div className="weather-grid">
                    <div className="weather-item">
                      <span>Temp</span>
                      <strong>
                        {weatherData.current?.temperature_c ?? weatherData.current_telemetry?.temperature_c ?? weatherData.temperature_c ?? '--'}°C
                      </strong>
                      <span style={{ fontSize: '0.65rem', color: 'var(--slate-400)' }}>
                        {t.apparentTemp}: {weatherData.current?.apparent_temperature_c ?? '--'}°C
                      </span>
                    </div>

                    <div className="weather-item">
                      <span>Humidity</span>
                      <strong>
                        {weatherData.current?.relative_humidity_pct ?? weatherData.current_telemetry?.relative_humidity_pct ?? weatherData.relative_humidity_pct ?? '--'}%
                      </strong>
                      <span style={{ fontSize: '0.65rem', color: 'var(--slate-400)' }}>
                        {weatherData.spray_window?.fungal_risk_level ? `Risk: ${weatherData.spray_window.fungal_risk_level}` : ''}
                      </span>
                    </div>

                    <div className="weather-item">
                      <span>Wind</span>
                      <strong>
                        {weatherData.current?.wind_speed_kmh ?? weatherData.current_telemetry?.wind_speed_kmh ?? weatherData.wind_speed_kmh ?? '--'} km/h
                      </strong>
                      <span style={{ fontSize: '0.65rem', color: 'var(--slate-400)' }}>
                        Gust: {weatherData.current?.wind_gusts_kmh ?? '--'} km/h
                      </span>
                    </div>

                    <div className="weather-item">
                      <span>Rain Prob</span>
                      <strong>
                        {weatherData.current?.precipitation_probability_6h ?? weatherData.current_telemetry?.precipitation_probability_6h ?? weatherData.precipitation_probability_6h ?? '0'}%
                      </strong>
                      <span style={{ fontSize: '0.65rem', color: 'var(--slate-400)' }}>
                        Rate: {weatherData.current?.precipitation_mm ?? 0} mm/h
                      </span>
                    </div>

                    <div className="weather-item">
                      <span>{t.surfacePressure}</span>
                      <strong>
                        {weatherData.current?.surface_pressure_hpa ?? 1013} hPa
                      </strong>
                    </div>

                    <div className="weather-item">
                      <span>{t.cloudCover}</span>
                      <strong>
                        {weatherData.current?.cloud_cover_pct ?? 0}%
                      </strong>
                    </div>
                  </div>

                  {/* Modeled Soil Moisture Telemetry */}
                  {weatherData.soil && (
                    <div className="soil-telemetry-box">
                      <div className="soil-header">
                        <h4>🌱 {t.soilMoistureTitle}</h4>
                        <span className="modeled-badge">🛰️ {t.modeledTag}</span>
                      </div>
                      <div className="soil-metric-row">
                        <span>
                          <strong>{weatherData.soil.soil_moisture_percentage}%</strong> (volumetric)
                        </span>
                        <span>
                          Temp: <strong>{weatherData.soil.soil_temperature_c}°C</strong>
                        </span>
                        <span className={`soil-status-pill ${weatherData.soil.moisture_status}`}>
                          {weatherData.soil.moisture_status}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Forecast Strip (24h / 7d toggle) */}
                  {(weatherData.hourly_24h?.length > 0 || weatherData.daily_7d?.length > 0) && (
                    <div className="forecast-strip-container">
                      <div className="forecast-tabs">
                        <button
                          className={`forecast-tab-btn ${forecastTab === 'hourly' ? 'active' : ''}`}
                          onClick={() => setForecastTab('hourly')}
                        >
                          🕒 {t.forecast24h}
                        </button>
                        <button
                          className={`forecast-tab-btn ${forecastTab === 'daily' ? 'active' : ''}`}
                          onClick={() => setForecastTab('daily')}
                        >
                          📅 {t.forecast7d}
                        </button>
                      </div>

                      {forecastTab === 'hourly' && weatherData.hourly_24h && (
                        <div className="hourly-scroll-strip">
                          {weatherData.hourly_24h.map((h, idx) => (
                            <div key={idx} className="hourly-mini-card">
                              <div className="hour-time">{h.time ? h.time.substring(11, 16) : `+${idx}h`}</div>
                              <div className="hour-temp">{h.temperature_c}°</div>
                              <div className="hour-rain">💧 {h.precipitation_probability}%</div>
                            </div>
                          ))}
                        </div>
                      )}

                      {forecastTab === 'daily' && weatherData.daily_7d && (
                        <div className="daily-forecast-list">
                          {weatherData.daily_7d.map((d, idx) => (
                            <div key={idx} className="daily-row">
                              <span className="day-name">{d.date}</span>
                              <span className="day-temps">{d.temp_max_c}° / {d.temp_min_c}°C</span>
                              <span className="day-rain">💧 {d.precipitation_probability_max}% ({d.precipitation_sum_mm}mm)</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Attribution & Location Footer */}
                  <div className="weather-footer-attribution">
                    <span>{weatherData.location_name || 'Maharashtra'}</span>
                    <span>{t.dataSourceTag}</span>
                  </div>
                </>
              )}
            </div>

          </div>

          {/* Right Column: Diagnostic XAI Results & Advisory */}
          <div className="right-col">
            {diagResult ? (
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <span>🔍</span> {t.resultsTitle}
                  </h3>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    {diagResult.is_local_inference ? (
                      <span className="edge-badge">{t.localInferenceBadge}</span>
                    ) : (
                      <span className="cloud-badge">{t.cloudInferenceBadge}</span>
                    )}
                    <span className="confidence-badge">
                      {t.calibratedConfidence}: {(diagResult.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* XAI Side-by-Side Visuals */}
                <div className="xai-grid">
                  <div className="xai-panel">
                    <div className="xai-panel-header">{t.originalLeaf}</div>
                    <img src={imagePreview} alt="Original Leaf" />
                  </div>
                  <div className="xai-panel">
                    <div className="xai-panel-header">{t.gradcamOverlay}</div>
                    {diagResult.heatmap_path ? (
                      <img src={`/${diagResult.heatmap_path}`} alt="Grad-CAM Overlay" />
                    ) : (
                      <div className="gradcam-offline-placeholder">
                        <span className="icon">📡</span>
                        <h5>Grad-CAM Requires Cloud Connectivity</h5>
                        <p>{t.gradcamOfflineNote}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Metrics Banner */}
                <div className="metrics-banner">
                  <div>
                    <div className="diag-name">
                      {diagResult.disease_name_multilingual?.[lang] || diagResult.predicted_class}
                    </div>
                    <div className="diag-sub">
                      Crop: {diagResult.crop.toUpperCase()}
                      {diagResult.crop_detection_method === 'auto_detected_classifier' && (
                        <span style={{ marginLeft: '0.5rem', color: '#38bdf8', fontWeight: 600 }}>
                          (🤖 AI Identified: {((diagResult.crop_detection_confidence || 0.99) * 100).toFixed(1)}%)
                        </span>
                      )}
                      {' | '}Model: {diagResult.model_version}
                      {diagResult.inference_time_ms && ` (${diagResult.inference_time_ms} ms)`}
                    </div>
                  </div>
                  {diagResult.details?.severity && (
                    <div className="hero-badge" style={{ background: '#059669', color: '#fff' }}>
                      {t.severityLevel}: {diagResult.details.severity} {diagResult.details.affected_area_percentage ? `(${diagResult.details.affected_area_percentage.toFixed(1)}%)` : ''}
                    </div>
                  )}
                </div>

                {/* Top-K Predictions Bar if Edge Inference */}
                {diagResult.top_predictions?.length > 1 && (
                  <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}>
                    <h5 style={{ fontSize: '0.8rem', fontWeight: 700, color: '#475569', marginBottom: '0.4rem' }}>
                      📊 Top Pathology Classifications:
                    </h5>
                    {diagResult.top_predictions.slice(0, 3).map((p, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                        <span>{p.disease}</span>
                        <strong>{p.confidence_percentage}%</strong>
                      </div>
                    ))}
                  </div>
                )}

                {/* Download PDF Field Advisory Action (When online) */}
                {isOnline && (
                  <div style={{ marginTop: '0.75rem', marginBottom: '0.75rem' }}>
                    <button
                      onClick={handleDownloadPdf}
                      disabled={pdfDownloading}
                      className="btn"
                      style={{
                        width: '100%',
                        background: '#065f46',
                        color: '#ffffff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        fontWeight: 600,
                        padding: '0.65rem 1rem',
                        borderRadius: '0.5rem',
                        cursor: pdfDownloading ? 'not-allowed' : 'pointer',
                        border: 'none',
                      }}
                    >
                      <span>📄</span>
                      {pdfDownloading ? t.downloadingPdf : t.downloadReportPdf}
                    </button>
                  </div>
                )}

                {/* Multimodal Crop Health & Microclimate Fusion Card */}
                {diagResult.details?.multimodal_assessment && (() => {
                  const mm = diagResult.details.multimodal_assessment;
                  const assessment = mm.multimodal_assessment || {};
                  const stresses = mm.weather_risk?.environmental_stresses || {};
                  const explain = mm.explainability || {};
                  const anomaly = assessment.anomaly_warning?.[lang] || assessment.anomaly_warning?.en;
                  const healthScore = assessment.crop_health_index ?? 75;
                  const velocity = assessment.disease_progression_velocity || "MODERATE";

                  return (
                    <div
                      style={{
                        background: 'rgba(15, 23, 42, 0.75)',
                        border: '1px solid #334155',
                        borderRadius: '0.75rem',
                        padding: '1rem',
                        marginTop: '0.75rem',
                        marginBottom: '0.75rem',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          borderBottom: '1px solid #1e293b',
                          paddingBottom: '0.5rem',
                          marginBottom: '0.75rem',
                        }}
                      >
                        <h4
                          style={{
                            fontSize: '0.95rem',
                            fontWeight: 700,
                            color: '#38bdf8',
                            margin: 0,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                          }}
                        >
                          <span>🌐</span> {t.multimodalTitle}
                        </h4>
                        <span
                          style={{
                            fontSize: '0.75rem',
                            padding: '0.2rem 0.5rem',
                            borderRadius: '0.375rem',
                            fontWeight: 600,
                            background:
                              assessment.is_environmentally_concordant
                                ? '#065f46'
                                : '#854d0e',
                            color: '#fff',
                          }}
                        >
                          {assessment.health_status_label || assessment.confidence_tier || 'CONCORDANT'}
                        </span>
                      </div>

                      {/* Composite Health Index & Progression Velocity */}
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                          gap: '0.5rem',
                          marginBottom: '0.75rem',
                        }}
                      >
                        <div
                          style={{
                            background: '#0f172a',
                            padding: '0.5rem 0.75rem',
                            borderRadius: '0.5rem',
                            border: '1px solid #1e293b',
                          }}
                        >
                          <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>{t.compositeHealthScore}</div>
                          <div
                            style={{
                              fontSize: '1.25rem',
                              fontWeight: 700,
                              color:
                                healthScore >= 70
                                  ? '#10b981'
                                  : healthScore >= 40
                                  ? '#f59e0b'
                                  : '#ef4444',
                            }}
                          >
                            {typeof healthScore === 'number' ? healthScore.toFixed(1) : healthScore} / 100
                          </div>
                        </div>

                        <div
                          style={{
                            background: '#0f172a',
                            padding: '0.5rem 0.75rem',
                            borderRadius: '0.5rem',
                            border: '1px solid #1e293b',
                          }}
                        >
                          <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>{t.infectionVelocity}</div>
                          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f59e0b' }}>
                            {velocity}
                          </div>
                        </div>
                      </div>

                      {/* Environmental Anomaly Alert Banner */}
                      {anomaly && (
                        <div
                          style={{
                            marginTop: '0.5rem',
                            padding: '0.5rem',
                            borderRadius: '0.375rem',
                            background: 'rgba(239, 68, 68, 0.15)',
                            border: '1px solid #ef4444',
                            color: '#fca5a5',
                            fontSize: '0.75rem',
                          }}
                        >
                          ⚠️ <strong>{t.anomalyAlert}:</strong> {anomaly}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Context-Aware Advisory */}
                {diagResult.details?.contextual_advisory && (
                  <div className="advisory-section">
                    <h4 className="advisory-title">
                      <span>📘</span> {t.advisoryTitle}
                    </h4>
                    <div className="advisory-body">
                      <p>
                        {diagResult.details.contextual_advisory.disease_overview?.[lang] ||
                         diagResult.details.contextual_advisory.disease_overview?.en}
                      </p>
                    </div>

                    {/* Cultural Practices */}
                    {diagResult.details.contextual_advisory.cultural_practices?.length > 0 && (
                      <div style={{ marginBottom: '1rem' }}>
                        <h5 style={{ fontSize: '0.85rem', color: '#064e3b', fontWeight: 700, marginBottom: '0.35rem' }}>
                          🌱 {t.culturalMethods}:
                        </h5>
                        <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: '#334155' }}>
                          {diagResult.details.contextual_advisory.cultural_practices.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* CIBRC Chemical Prescriptions */}
                    {diagResult.details.contextual_advisory.chemical_prescriptions?.map((chem, idx) => (
                      <div key={idx} className="chemical-card">
                        <h5>🧪 {chem.chemical_name}</h5>
                        <p><strong>Dose:</strong> {chem.dosage} ({chem.dilution})</p>
                        <p><strong>Method:</strong> {chem.application_method}</p>
                        {chem.phi_days && (
                          <div className="phi-badge">⏳ Pre-Harvest Interval (PHI): {chem.phi_days} Days</div>
                        )}
                      </div>
                    ))}

                    {/* Statutory Notice */}
                    <div className="statutory-notice">
                      ⚖️ {diagResult.details.contextual_advisory.statutory_disclaimer?.[lang] ||
                          diagResult.details.contextual_advisory.statutory_disclaimer?.en}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem', color: '#64748b' }}>
                <div style={{ fontSize: '3rem', marginBottom: '0.75rem' }}>🌿</div>
                <h3 style={{ color: '#1e293b', marginBottom: '0.5rem' }}>Ready for Crop Leaf Diagnosis</h3>
                <p style={{ maxWidth: '420px', margin: '0 auto', fontSize: '0.9rem' }}>
                  Upload a crop leaf photograph on the left to inspect native PyTorch inference, Grad-CAM visual heatmaps, or run on-device Edge WASM AI directly offline.
                </p>
              </div>
            )}

            {/* Embedded Multilingual RAG Assistant Drawer */}
            <div className="rag-chat-drawer">
              <div className="chat-header">
                <span>🤖</span> {t.chatTitle}
              </div>

              {/* Chat Message List */}
              <div className="chat-messages">
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`chat-msg ${msg.sender}`}>
                    <p>{msg.text}</p>
                    {msg.sources?.length > 0 && (
                      <div>
                        {msg.sources.map((s, si) => (
                          <span key={si} className="citation">
                            📚 {s.source_name || s.organization}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {chatLoading && (
                  <div className="chat-msg bot">
                    <em>{t.thinking}</em>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>

              {/* Quick Prompt Chips */}
              <div className="chat-chips">
                {t.quickQuestions.map((q, qi) => (
                  <button key={qi} className="chip-btn" onClick={() => handleSendMessage(q)}>
                    {q}
                  </button>
                ))}
              </div>

              {/* Chat Input Bar */}
              <div className="chat-input-row">
                <input
                  type="text"
                  className="chat-input"
                  placeholder={t.chatPlaceholder}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                />
                <button
                  className="chat-send-btn"
                  onClick={() => handleSendMessage()}
                  disabled={chatLoading}
                >
                  {t.send}
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Offline Agricultural Guide Modal */}
      {showOfflineModal && (
        <div className="offline-modal-overlay" onClick={() => setShowOfflineModal(false)}>
          <div className="offline-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="offline-modal-header">
              <h3>📖 {t.offlineGuideTitle}</h3>
              <button className="close-btn" onClick={() => setShowOfflineModal(false)}>✕</button>
            </div>
            <div className="offline-modal-body">
              <input
                type="text"
                className="offline-search-input"
                placeholder={t.searchOfflinePlaceholder}
                value={offlineSearch}
                onChange={async (e) => {
                  const val = e.target.value;
                  setOfflineSearch(val);
                  const res = await searchOfflineKnowledge(crop !== 'auto' ? crop : null, val, lang);
                  setOfflineChunks(res);
                }}
              />
              <div className="offline-chunks-list">
                {offlineChunks.map((c, i) => (
                  <div key={i} className="offline-chunk-card">
                    <h4>{c.disease_name || c.crop} ({c.section})</h4>
                    <p>{c.text}</p>
                  </div>
                ))}
                {offlineChunks.length === 0 && (
                  <p className="no-data-text">{lang === 'mr' ? 'कोणतीही ऑफलाइन माहिती सापडली नाही.' : 'No offline knowledge chunks found.'}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Diagnosis History Modal */}
      {showHistoryModal && (
        <div className="offline-modal-overlay" onClick={() => setShowHistoryModal(false)}>
          <div className="offline-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="offline-modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <h3>📋 {t.offlineHistoryTitle} ({historyList.length})</h3>
                <button
                  onClick={handleExportHistory}
                  style={{
                    background: '#0284c7',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '0.25rem 0.6rem',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  📥 {t.exportHistory}
                </button>
              </div>
              <button className="close-btn" onClick={() => setShowHistoryModal(false)}>✕</button>
            </div>
            <div className="offline-modal-body">
              {/* Storage Meter */}
              <div className="storage-meter">
                <span>💾 {t.storageUsage}: <strong>{storageInfo.usageMB} MB</strong></span>
                <span>Quota: <strong>{storageInfo.quotaMB} MB</strong> ({storageInfo.percentUsed}%)</span>
              </div>

              {/* History Items List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {historyList.map((item) => (
                  <div
                    key={item.diagnosis_id}
                    className="history-card-item"
                    onClick={() => handleSelectHistoryItem(item)}
                  >
                    <img
                      src={item.image_reference || '/pwa-192x192.png'}
                      alt={item.predicted_disease}
                      className="history-card-thumb"
                    />
                    <div className="history-card-info">
                      <h4>{item.predicted_disease}</h4>
                      <p>
                        Crop: <strong>{item.crop_type.toUpperCase()}</strong> | Confidence: <strong>{(item.confidence * 100).toFixed(1)}%</strong>
                      </p>
                      <p style={{ marginTop: '0.15rem' }}>
                        📅 {new Date(item.diagnosis_timestamp).toLocaleString()}
                      </p>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.4rem' }}>
                      <span className={`sync-status-pill ${item.sync_status}`}>
                        {item.sync_status === 'synced'
                          ? `🟢 ${t.syncStatusSynced}`
                          : item.sync_status === 'pending_sync'
                          ? `🟠 ${t.syncStatusPending}`
                          : `⚡ ${t.syncStatusLocalOnly}`}
                      </span>
                      <button
                        onClick={(e) => handleDeleteHistory(item.diagnosis_id, e)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#ef4444',
                          fontSize: '0.8rem',
                          cursor: 'pointer',
                          padding: '0.2rem'
                        }}
                        title="Delete record"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
                {historyList.length === 0 && (
                  <p className="no-data-text">{t.noOfflineHistory}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
