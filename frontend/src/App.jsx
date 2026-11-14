import React, { useState, useEffect, useRef } from 'react';
import './styles/claude-theme.css';
import { translations } from './i18n/translations';
import Sidebar from './components/Sidebar';
import ArtifactPanel from './components/ArtifactPanel';
import InputBar from './components/InputBar';
import FarmModal from './components/FarmModal';
import KvkModal from './components/KvkModal';
import OfflineGuideModal from './components/OfflineGuideModal';
import ProfileModal from './components/ProfileModal';

import { syncManager } from './offline/syncManager';
import {
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

import {
  PanelLeft,
  PanelLeftClose,
  Maximize2,
  FileText,
  Sprout,
  Sun,
  CloudRain,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Cpu
} from 'lucide-react';

export default function App() {
  const [lang, setLang] = useState('mr'); // Default Marathi for regional farmers
  const [crop, setCrop] = useState('auto');
  const [district, setDistrict] = useState('pune');
  const [districtsList, setDistrictsList] = useState([]);
  const [gpsLocation, setGpsLocation] = useState(null);
  const [weatherData, setWeatherData] = useState(null);

  // Multimodal Prompt State
  const [inputText, setInputText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [useEdgeAi, setUseEdgeAi] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Active Diagnosis & Claude Artifact State
  const [diagResult, setDiagResult] = useState(null);
  const [activeArtifactOpen, setActiveArtifactOpen] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);

  // Conversational Chat Feed State
  const [chatMessages, setChatMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  // Layout & Navigation State
  const [sidebarOpen, setSidebarOpen] = useState(() => (typeof window !== 'undefined' ? window.innerWidth >= 768 : true));

  const handleMobileDismissSidebar = () => {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  // Farm Plots State (SRS FR-005 to FR-008)
  const [farms, setFarms] = useState(() => {
    try {
      const saved = localStorage.getItem('pikvaidya_farms');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return [
      { id: '1', name: 'Gat No. 104 (East Plot)', crop: 'sugarcane', variety: 'Co 86032', area: 3.5, soil_type: 'Black Cotton', irrigation: 'Drip' },
      { id: '2', name: 'Wadi Plot (Tomato)', crop: 'tomato', variety: 'Abhinav', area: 1.5, soil_type: 'Red Loam', irrigation: 'Drip' }
    ];
  });
  const [activeFarmId, setActiveFarmId] = useState('1');

  // Offline & Edge AI State
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [queueStats, setQueueStats] = useState({ pendingCount: 0, failedCount: 0, totalQueued: 0 });
  const [isSyncing, setIsSyncing] = useState(false);
  const [historyList, setHistoryList] = useState([]);
  const [storageInfo, setStorageInfo] = useState({ usageMB: '0.00', quotaMB: '0.00', percentUsed: 0 });
  const [modelCachedMap, setModelCachedMap] = useState({ sugarcane: false, tomato: false, onion: false });
  const [cachingCrop, setCachingCrop] = useState(null);

  // Farmer Profile State (SRS FR-001 - FR-004, FR-007)
  const [profile, setProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('pikvaidya_profile');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return {
      name: 'Ramesh Patil',
      mobile: '9822012345',
      district: 'pune',
      locationConsent: true,
      notifyConsent: true
    };
  });

  // Modals
  const [showFarmModal, setShowFarmModal] = useState(false);
  const [showKvkModal, setShowKvkModal] = useState(false);
  const [showOfflineGuideModal, setShowOfflineGuideModal] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);

  const t = translations[lang] || translations.en;
  const feedEndRef = useRef(null);

  // Save farms to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('pikvaidya_farms', JSON.stringify(farms));
    } catch (e) {}
  }, [farms]);

  // Save profile to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('pikvaidya_profile', JSON.stringify(profile));
      if (profile.district && profile.district !== district) {
        setDistrict(profile.district);
      }
    } catch (e) {}
  }, [profile]);

  // Sync / Offline listeners
  useEffect(() => {
    const unsubNet = syncManager.addNetworkListener((online) => {
      setIsOnline(online);
      refreshQueue();
    });

    const unsubSync = syncManager.addSyncListener(() => {
      refreshQueue();
      loadHistory();
    });

    refreshQueue();
    refreshStorage();
    checkModelCaches();
    loadHistory();

    return () => {
      unsubNet();
      unsubSync();
    };
  }, []);

  const refreshQueue = async () => {
    try {
      const stats = await getSyncQueueStats();
      setQueueStats(stats);
    } catch (e) {}
  };

  const refreshStorage = async () => {
    try {
      const est = await getStorageEstimate();
      setStorageInfo(est);
    } catch (e) {}
  };

  const checkModelCaches = async () => {
    try {
      const [sc, tm, on] = await Promise.all([
        isModelCached('sugarcane'),
        isModelCached('tomato'),
        isModelCached('onion')
      ]);
      setModelCachedMap({ sugarcane: sc, tomato: tm, onion: on });
    } catch (e) {}
  };

  const loadHistory = async () => {
    try {
      const list = await getAllDiagnoses({ limit: 40 });
      setHistoryList(list || []);
    } catch (e) {}
  };

  // Fetch Maharashtra districts
  useEffect(() => {
    async function fetchDistricts() {
      try {
        const res = await fetch('/api/v1/weather/locations');
        if (res.ok) {
          const data = await res.json();
          setDistrictsList(data.locations || []);
        }
      } catch (err) {}
    }
    fetchDistricts();
  }, []);

  // Fetch weather telemetry whenever district or GPS changes
  useEffect(() => {
    async function fetchWeather() {
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
      } catch (err) {}
    }
    fetchWeather();
  }, [district, gpsLocation]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isLoading]);

  // GPS Location handler
  const handleUseGps = () => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setGpsLocation({
            lat: pos.coords.latitude,
            lon: pos.coords.longitude
          });
        },
        (err) => alert('GPS error: ' + err.message)
      );
    }
  };

  // Image selection
  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleRemoveImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
  };

  // Model Caching
  const handlePreloadModel = async (targetCrop) => {
    try {
      setCachingCrop(targetCrop);
      await cacheModelForOffline(targetCrop);
      setModelCachedMap((prev) => ({ ...prev, [targetCrop]: true }));
      refreshStorage();
    } catch (err) {
      alert(`Model preloading failed: ${err.message}`);
    } finally {
      setCachingCrop(null);
    }
  };

  // History Actions
  const handleSelectHistory = (item) => {
    setImagePreview(item.image_reference);
    setDiagResult({
      crop: item.crop_type,
      crop_detection_method: item.is_local_inference ? 'edge_onnx_wasm_int8' : 'cloud_pytorch',
      predicted_class: item.predicted_disease,
      disease_name_multilingual: { en: item.predicted_disease, mr: item.predicted_disease, hi: item.predicted_disease },
      confidence: item.confidence,
      heatmap_path: item.gradcam_reference,
      is_local_inference: item.is_local_inference,
      model_version: item.is_local_inference ? 'MobileNetV3 INT8 Edge WASM' : 'PikVaidya Cloud PyTorch',
      details: {
        severity: item.risk_level || 'ANALYZED'
      },
      recommendations: {
        cultural: item.recommendations?.length > 0 ? [item.recommendations[0]] : [],
        chemical: item.recommendations?.length > 1 ? item.recommendations.slice(1) : []
      }
    });
    setActiveArtifactOpen(true);
    handleMobileDismissSidebar();
  };

  const handleDeleteHistory = async (diagId) => {
    await deleteDiagnosis(diagId);
    await loadHistory();
    await refreshStorage();
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

  // Farm Plots Actions
  const handleSelectFarm = (id) => {
    setActiveFarmId(id);
    const plot = farms.find((f) => f.id === id);
    if (plot && plot.crop) {
      setCrop(plot.crop);
    }
    handleMobileDismissSidebar();
  };

  const handleSaveFarm = (farmRecord) => {
    setFarms((prev) => [farmRecord, ...prev]);
    setActiveFarmId(farmRecord.id);
    setCrop(farmRecord.crop);
    setShowFarmModal(false);
  };

  const handleDeleteFarm = (id) => {
    setFarms((prev) => prev.filter((f) => f.id !== id));
  };

  // Download PDF Field Advisory Report
  const handleDownloadPdf = async () => {
    if (!diagResult) return;
    setPdfDownloading(true);

    try {
      const payload = {
        crop: diagResult.crop || crop,
        disease_name: diagResult.predicted_class,
        confidence: diagResult.confidence,
        severity: diagResult.details?.severity || 'MODERATE',
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

  // Main Submit Handler (Multimodal Send)
  const handleSend = async () => {
    const textToSend = inputText.trim();
    const hasImage = !!selectedImage;

    if (!textToSend && !hasImage) return;

    setIsLoading(true);

    // 1. If an image is attached, run diagnosis!
    if (hasImage) {
      const userMessage = {
        sender: 'user',
        text: textToSend || (lang === 'mr' ? 'पानाचे रोग निदान करा.' : 'Analyze this crop leaf.'),
        image: imagePreview
      };
      setChatMessages((prev) => [...prev, userMessage]);

      const capturedPreview = imagePreview;
      const targetCrop = crop === 'auto' ? 'sugarcane' : crop;

      // Check if should run on Edge WASM
      if (useEdgeAi || !isOnline) {
        try {
          const edgeResult = await runLocalEdgeInference(targetCrop, capturedPreview);

          await queueOfflineDiagnosis({
            image_data: capturedPreview,
            image_name: selectedImage.name,
            crop: targetCrop,
            district,
            latitude: gpsLocation?.lat || null,
            longitude: gpsLocation?.lon || null,
            captured_at: new Date().toISOString(),
            client_preview: edgeResult,
            is_local_inference: true,
            farm_id: activeFarm ? activeFarm.id : null,
            farm_name: activeFarm ? activeFarm.name : null
          });

          await refreshQueue();
          await loadHistory();
          await refreshStorage();

          const normalizedResult = {
            crop: targetCrop,
            predicted_class: edgeResult.predicted_disease,
            disease_name_multilingual: { en: edgeResult.predicted_disease, mr: edgeResult.predicted_disease, hi: edgeResult.predicted_disease },
            confidence: edgeResult.confidence,
            heatmap_path: null,
            is_local_inference: true,
            model_version: `MobileNetV3 INT8 Edge WASM (${edgeResult.inference_time_ms}ms)`,
            top_predictions: edgeResult.top_predictions,
            details: {
              severity: 'ON_DEVICE_ANALYSIS',
              contextual_advisory: {
                cultural_practices: edgeResult.recommendations.slice(0, 1),
                chemical_prescriptions: []
              }
            }
          };

          setDiagResult(normalizedResult);
          setActiveArtifactOpen(true);

          setChatMessages((prev) => [
            ...prev,
            {
              sender: 'assistant',
              text: lang === 'mr'
                ? `⚡ ऑन-डिव्हाइस Edge AI (WASM INT8) द्वारे अवघ्या ${edgeResult.inference_time_ms}ms मध्ये निदान पूर्ण झाले: **${edgeResult.predicted_disease}** (अचूकता: ${edgeResult.confidence_percentage}%).`
                : `⚡ Local on-device diagnosis completed in ${edgeResult.inference_time_ms}ms: **${edgeResult.predicted_disease}** (Confidence: ${edgeResult.confidence_percentage}%).`,
              isDiagnosticArtifact: true,
              result: normalizedResult
            }
          ]);
        } catch (err) {
          setChatMessages((prev) => [
            ...prev,
            { sender: 'assistant', text: `Edge AI Error: ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
          setSelectedImage(null);
          setImagePreview(null);
          setInputText('');
        }
        return;
      }

      // Cloud PyTorch Diagnosis with Grad-CAM
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

        let response = await fetch('/api/crop-health/predict', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          response = await fetch('/api/v1/diagnose', {
            method: 'POST',
            body: formData
          });
        }

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          const errMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail || '');
          const isFoliarRejection = response.status === 422 || errMsg.toLowerCase().includes('foliage') || errMsg.toLowerCase().includes('leaf') || errMsg.toLowerCase().includes('quality');

          if (isFoliarRejection) {
            setChatMessages((prev) => [
              ...prev,
              {
                sender: 'assistant',
                isQualityAlert: true,
                text: lang === 'mr'
                  ? "🌿 **पानाच्या दर्जा तपासणीत त्रुटी (Foliar Area < 15%)**\n\nअपलोड केलेल्या छायाचित्रात पुरेसे हिरवे पान किंवा रोगाचे स्पष्ट लक्षण आढळले नाही. अचूक निदानासाठी कृपया खालील सूचनांचे पालन करा:"
                  : "🌿 **Foliage Quality Check Notice (< 15% Leaf Surface Area)**\n\nThe image was rejected by our foliar geometry filter because insufficient crop leaf area was detected. For an accurate neural diagnosis, please capture a new photo with these tips:",
                tips: [
                  lang === 'mr' ? "पानाचा संपूर्ण पृष्ठभाग कॅमेऱ्याच्या मध्यभागी ठेवा." : "Center the diseased leaf blade directly in the camera frame.",
                  lang === 'mr' ? "सावली किंवा तीव्र प्रकाशाचे चकाकणे टाळा (नैसर्गिक उजेडात फोटो घ्या)." : "Use diffused natural daylight (avoid harsh glare or deep shadows).",
                  lang === 'mr' ? "रोगाचे डाग/ठिपके स्पष्ट दिसतील असे स्पष्ट लक्ष केंद्रित (Focus) करा." : "Ensure diseased spots and lesions are in sharp focus.",
                  lang === 'mr' ? "हाताची बोटे किंवा मातीपेक्षा पानावरील भाग जास्तीत जास्त व्यापेल याची खात्री करा." : "Keep the leaf occupying at least 60% of the frame without hand obstruction."
                ]
              }
            ]);
            return;
          }

          throw new Error(errMsg || `Diagnosis failed (HTTP ${response.status})`);
        }

        const data = await response.json();
        
        // Normalize between /api/crop-health/predict and /api/v1/diagnose
        const normalized = {
          crop: data.crop_type || data.crop || crop,
          crop_detection_method: data.crop_detection_method || 'explicit_user_selection',
          predicted_class: data.predicted_disease || data.predicted_class,
          disease_name_multilingual: data.disease_name_multilingual || {
            en: data.predicted_disease || data.predicted_class,
            mr: data.predicted_disease || data.predicted_class,
            hi: data.predicted_disease || data.predicted_class
          },
          confidence: data.model_confidence ?? data.confidence ?? 0.9,
          heatmap_path: data.gradcam_image_url || data.heatmap_path || data.image_prediction?.heatmap_path,
          model_version: data.image_prediction?.model_version || data.model_version || 'PikVaidya Cloud PyTorch',
          details: {
            severity: data.image_prediction?.foliar_severity || data.details?.severity || 'ANALYZED',
            affected_area_percentage: data.image_prediction?.affected_area_percentage,
            multimodal_assessment: data.combined_assessment ? {
              multimodal_assessment: data.combined_assessment,
              weather_risk: data.environmental_risk
            } : data.details?.multimodal_assessment,
            contextual_advisory: {
              cultural_practices: data.advisory_recommendations?.cultural_practices || data.details?.contextual_advisory?.cultural_practices || [],
              chemical_prescriptions: data.advisory_recommendations?.chemical_prescriptions || data.details?.contextual_advisory?.chemical_prescriptions || [],
              disease_overview: data.details?.contextual_advisory?.disease_overview || {
                en: `Detected ${data.predicted_disease || data.predicted_class} with ${((data.model_confidence ?? data.confidence ?? 0.9) * 100).toFixed(1)}% confidence.`
              },
              statutory_disclaimer: data.statutory_disclaimer ? { en: data.statutory_disclaimer } : data.details?.contextual_advisory?.statutory_disclaimer
            }
          }
        };

        setDiagResult(normalized);
        setActiveArtifactOpen(true);

        // Save to IndexedDB history with farm association
        await saveDiagnosis({
          crop_type: normalized.crop,
          predicted_disease: normalized.predicted_class,
          confidence: normalized.confidence,
          image_reference: capturedPreview,
          gradcam_reference: normalized.heatmap_path,
          latitude: gpsLocation?.lat || null,
          longitude: gpsLocation?.lon || null,
          diagnosis_timestamp: new Date().toISOString(),
          sync_status: 'synced',
          is_local_inference: false,
          farm_id: activeFarm ? activeFarm.id : null,
          farm_name: activeFarm ? activeFarm.name : null,
          recommendations: normalized.details?.contextual_advisory?.cultural_practices || []
        });

        await loadHistory();
        await refreshStorage();

        const diseaseName = normalized.disease_name_multilingual?.[lang] || normalized.predicted_class;
        const confidencePct = (normalized.confidence * 100).toFixed(1);

        setChatMessages((prev) => [
          ...prev,
          {
            sender: 'assistant',
            text: lang === 'mr'
              ? `🔬 **${diseaseName}** चे निदान झाले आहे (कॅलिब्रेटेड अचूकता: ${confidencePct}%). तपशीलवार Grad-CAM लक्षवेध नकाशा व ICAR/CIBRC फवारणी सल्ला उजव्या कॅनव्हासमध्ये उघडण्यात आला आहे.`
              : `🔬 Verified **${diseaseName}** with ${confidencePct}% calibrated confidence. Grad-CAM visual explainability heatmap and ICAR/CIBRC prescriptions are loaded in the diagnostic canvas.`,
            isDiagnosticArtifact: true,
            result: normalized,
            sources: [{ source_name: 'ICAR Package of Practices' }, { source_name: 'CIBRC Registered Fungicides' }]
          }
        ]);
      } catch (err) {
        setChatMessages((prev) => [
          ...prev,
          { sender: 'assistant', text: `Diagnostic Error: ${err.message}` }
        ]);
      } finally {
        setIsLoading(false);
        setSelectedImage(null);
        setImagePreview(null);
        setInputText('');
      }
      return;
    }

    // 2. Pure Agronomic Text Query
    await executeAgronomicQuery(textToSend, crop !== 'auto' ? crop : null);
  };

  const executeAgronomicQuery = async (queryText, targetCrop = null) => {
    const textToSend = (queryText || '').trim();
    if (!textToSend) return;

    const activeCropType = targetCrop || (crop !== 'auto' ? crop : (diagResult?.crop || 'sugarcane'));
    if (targetCrop && targetCrop !== crop) {
      setCrop(targetCrop);
    }

    const userMessage = { sender: 'user', text: textToSend };
    setChatMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    // If offline, search client IndexedDB knowledge chunks
    if (!isOnline) {
      try {
        const localChunks = await searchOfflineKnowledge(activeCropType !== 'auto' ? activeCropType : null, textToSend, lang);
        if (localChunks.length > 0) {
          setChatMessages((prev) => [
            ...prev,
            {
              sender: 'assistant',
              text: `[ऑफलाइन माहिती] ${localChunks[0].text}`,
              sources: [{ source_name: localChunks[0].source || 'ICAR Offline Cache' }]
            }
          ]);
        } else {
          setChatMessages((prev) => [
            ...prev,
            {
              sender: 'assistant',
              text: lang === 'mr'
                ? 'ऑफलाइन उपलब्ध माहितीमध्ये उत्तर सापडले नाही. इंटरनेट जोडणी झाल्यावर पूर्ण RAG उत्तरे मिळतील.'
                : 'No matching offline knowledge found. Online connection required for comprehensive RAG assistant.'
            }
          ]);
        }
      } catch (err) {
        setChatMessages((prev) => [
          ...prev,
          { sender: 'assistant', text: `Offline Search Error: ${err.message}` }
        ]);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // Online RAG Chat Assistant
    try {
      const payload = {
        message: textToSend,
        crop: activeCropType !== 'auto' ? activeCropType : 'sugarcane',
        language: lang,
        preferred_language: lang,
        session_id: sessionId,
        diagnostic_context: diagResult ? {
          crop: diagResult.crop,
          predicted_disease: diagResult.predicted_class,
          confidence: diagResult.confidence,
          severity: diagResult.details?.severity || 'MODERATE'
        } : null,
        weather_context: weatherData?.current ? {
          temperature_c: weatherData.current.temperature_c,
          relative_humidity_pct: weatherData.current.relative_humidity_pct,
          wind_speed_kmh: weatherData.current.wind_speed_kmh,
          is_safe_to_spray: weatherData.spray_window?.status === 'optimal'
        } : null
      };

      const res = await fetch('/api/v1/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Assistant query failed (HTTP ${res.status})`);
      }

      const data = await res.json();
      if (data.session_id) setSessionId(data.session_id);

      const replyText = data.reply || data.answer || '';
      const recs = data.key_recommendations || [];
      const disclaimer = data.statutory_disclaimer || '';

      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: replyText,
          recommendations: recs,
          disclaimer: disclaimer,
          sources: data.sources || data.retrieved_sources || []
        }
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { sender: 'assistant', text: `Assistant Error: ${err.message}` }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (promptQuery, targetCrop = null) => {
    if (targetCrop === 'weather') {
      const userMsg = {
        sender: 'user',
        text: lang === 'mr'
          ? '🌦️ महाराष्ट्रातील शेताचे सूक्ष्म हवामान व फवारणी अनुकूलता तपासा.'
          : '🌦️ Check real-time microclimate spray safety and 14-day weather risk.'
      };
      setChatMessages((prev) => [
        ...prev,
        userMsg,
        {
          sender: 'assistant',
          isWeatherCard: true,
          text: lang === 'mr'
            ? `📍 **${weatherData?.location_name || district.toUpperCase()} (महाराष्ट्र)** हवामान व फवारणी अनुकूलता अहवाल:`
            : `📍 Microclimate Spray Window Report for **${weatherData?.location_name || district.toUpperCase()}, Maharashtra**:`,
          weather: weatherData
        }
      ]);
      return;
    }
    executeAgronomicQuery(promptQuery, targetCrop);
  };

  const activeFarm = farms.find((f) => f.id === activeFarmId);

  return (
    <div className="app-root">
      {/* Mobile Backdrop Overlay */}
      {sidebarOpen && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar backdrop"
        />
      )}

      {/* Claude-Style Collapsible Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        lang={lang}
        onLangChange={setLang}
        t={t}
        isOnline={isOnline}
        queueStats={queueStats}
        onManualSync={() => syncManager.syncNow()}
        isSyncing={isSyncing}
        farms={farms}
        activeFarmId={activeFarmId}
        onSelectFarm={handleSelectFarm}
        onOpenFarmModal={() => setShowFarmModal(true)}
        historyList={historyList}
        onSelectHistory={handleSelectHistory}
        onDeleteHistory={handleDeleteHistory}
        onExportHistory={handleExportHistory}
        onNewAnalysis={() => {
          setDiagResult(null);
          setActiveArtifactOpen(false);
          setChatMessages([]);
          setSelectedImage(null);
          setImagePreview(null);
          setInputText('');
          handleMobileDismissSidebar();
        }}
        onOpenOfflineGuide={() => setShowOfflineGuideModal(true)}
        storageInfo={storageInfo}
        onPreloadModel={handlePreloadModel}
        modelCachedMap={modelCachedMap}
        cachingCrop={cachingCrop}
        profile={profile}
        onOpenProfile={() => setShowProfileModal(true)}
        onCloseMobile={handleMobileDismissSidebar}
      />

      {/* Main Workspace Column */}
      <div className="claude-main-wrapper">
        {/* Top Navbar */}
        <header className="claude-topbar">
          <div className="topbar-left">
            {!sidebarOpen && (
              <button
                className="sidebar-toggle-btn"
                onClick={() => setSidebarOpen(true)}
                title="Expand Sidebar"
              >
                <PanelLeft size={18} />
              </button>
            )}

            {/* Farm & Crop Breadcrumb */}
            <div className="topbar-breadcrumb">
              <span className="topbar-farm-name">
                {activeFarm ? activeFarm.name : 'PikVaidya Farm'}
              </span>
              <span style={{ color: 'var(--text-light)' }}>/</span>
              <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                {crop === 'auto' ? 'Auto-Detect' : crop}
              </span>
            </div>
          </div>

          <div className="topbar-right">
            {/* Live Microclimate Spray Pill */}
            {weatherData?.spray_window && (
              <div
                className="topbar-spray-pill"
                style={{
                  backgroundColor:
                    weatherData.spray_window.status === 'optimal'
                      ? 'var(--status-optimal-bg)'
                      : 'var(--status-warning-bg)',
                  color:
                    weatherData.spray_window.status === 'optimal'
                      ? 'var(--status-optimal-text)'
                      : 'var(--status-warning-text)'
                }}
              >
                <CloudRain size={13} />
                <span>
                  {weatherData.spray_window.status === 'optimal' ? 'Spray: GO' : 'Spray: Caution'}
                </span>
                <span className="spray-pill-temp">({weatherData.current?.temperature_c ?? '--'}°C)</span>
              </div>
            )}

            {/* Artifact Toggle Button if active diagnosis exists */}
            {diagResult && (
              <button
                className="topbar-btn"
                onClick={() => setActiveArtifactOpen(!activeArtifactOpen)}
                style={{
                  background: activeArtifactOpen ? 'var(--accent-terracotta-light)' : 'transparent',
                  color: activeArtifactOpen ? 'var(--accent-terracotta)' : 'var(--text-secondary)'
                }}
              >
                <FileText size={15} />
                <span>{activeArtifactOpen ? 'Hide' : 'Artifact'}</span>
              </button>
            )}
          </div>
        </header>

        {/* Split Canvas: Conversational Feed + Claude Artifact Panel */}
        <div className="claude-split-canvas">
          {/* Conversational Stream */}
          <div className="claude-feed-column">
            <div className="claude-feed-scroll">
              <div className="feed-max-width">
                {/* Empty State / Hero Greeting (Claude Style) */}
                {chatMessages.length === 0 && (
                  <div className="claude-hero-container">
                    <div className="claude-hero-leaf-badge">
                      <Sprout size={28} />
                    </div>

                    <h2 className="claude-hero-heading">
                      {lang === 'mr'
                        ? `शुभ दुपार, ${profile.name ? profile.name.split(' ')[0] : 'शेतकरी'} मित्र.`
                        : lang === 'hi'
                        ? `शुभ दोपहर, ${profile.name ? profile.name.split(' ')[0] : 'किसान'} मित्र.`
                        : `Good afternoon, ${profile.name ? profile.name.split(' ')[0] : 'Shetkari Mitra'}.`}
                    </h2>

                    <p className="claude-hero-sub">
                      {lang === 'mr'
                        ? 'पानाचा फोटो जोडून अचूक रोग निदान व Grad-CAM दृश्य स्पष्टीकरण मिळवा, किंवा ICAR आणि CIBRC प्रमाणित शेती सल्ला विचारा.'
                        : 'Upload a crop leaf photograph for instant explainable pathology diagnosis with Grad-CAM, or ask agronomic queries grounded in verified ICAR & CIBRC packages of practices.'}
                    </p>

                    {/* Claude-Style Suggestion Cards */}
                    <div className="hero-suggestions-grid">
                      <div
                        className="suggestion-card"
                        onClick={() => handleSuggestionClick(
                          lang === 'mr'
                            ? 'उसावरील लाल कुजव्या व तांबेरा रोगावर कोणते बुरशीनाशक वापरावे आणि ICAR शिफारसी काय आहेत?'
                            : lang === 'hi'
                            ? 'गन्ने के लाल सड़न (Red Rot) रोग पर कौन सी दवा और मात्रा उपयोगी है?'
                            : 'What fungicide cures sugarcane red rot and what is the dose per liter?',
                          'sugarcane'
                        )}
                      >
                        <span className="suggestion-icon">🍬</span>
                        <div className="suggestion-title">
                          {lang === 'mr' ? 'ऊस: तांबेरा व लाल कुजव्या नियंत्रण' : 'Sugarcane: Red Rot & Rust Control'}
                        </div>
                        <div className="suggestion-desc">
                          {lang === 'mr' ? 'ICAR-SBI प्रमाणित बुरशीनाशक मात्रा व प्रतिबंधक उपाय' : 'ICAR-SBI recommended fungicides and sett treatment'}
                        </div>
                      </div>

                      <div
                        className="suggestion-card"
                        onClick={() => handleSuggestionClick(
                          lang === 'mr'
                            ? 'टोमॅटोच्या करपा रोगासाठी योग्य फवारणी आणि CIBRC शिफारस केलेले बुरशीनाशक कोणते?'
                            : lang === 'hi'
                            ? 'टमाटर के अगेती झुलसा (Early Blight) रोग के लिए अनुशंसित कीटनाशक और समय क्या है?'
                            : 'What is the spray timing and CIBRC chemical for tomato early blight?',
                          'tomato'
                        )}
                      >
                        <span className="suggestion-icon">🍅</span>
                        <div className="suggestion-title">
                          {lang === 'mr' ? 'टोमॅटो: करपा व विषाणू नियंत्रण' : 'Tomato: Early Blight & TYLCV'}
                        </div>
                        <div className="suggestion-desc">
                          {lang === 'mr' ? 'अल्टरनेरिया करपा आणि पांढरी माशी नियंत्रण सल्ला' : 'Alternaria blight fungicide spray and whitefly vector safety'}
                        </div>
                      </div>

                      <div
                        className="suggestion-card"
                        onClick={() => handleSuggestionClick(
                          lang === 'mr'
                            ? 'कांद्यावरील जांभळा करपा (Purple Blotch) रोखण्यासाठी ICAR-DOGR प्रमाणित फवारणी सल्ला काय आहे?'
                            : lang === 'hi'
                            ? 'प्याज के बैंगनी धब्बा (Purple Blotch) रोग की पहचान और नियंत्रण के उपाय क्या हैं?'
                            : 'How to identify and control onion purple blotch in rainy weather?',
                          'onion'
                        )}
                      >
                        <span className="suggestion-icon">🧅</span>
                        <div className="suggestion-title">
                          {lang === 'mr' ? 'कांदा: जांभळा करपा प्रतिबंध' : 'Onion: Purple Blotch Mitigation'}
                        </div>
                        <div className="suggestion-desc">
                          {lang === 'mr' ? 'ICAR-DOGR प्रमाणित फवारणी व Pre-Harvest Interval (PHI)' : 'ICAR-DOGR approved spray schedules & PHI wait days'}
                        </div>
                      </div>

                      <div
                        className="suggestion-card"
                        onClick={() => handleSuggestionClick('Check microclimate spray safety', 'weather')}
                      >
                        <span className="suggestion-icon">🌦️</span>
                        <div className="suggestion-title">
                          {lang === 'mr' ? 'हवामान व फवारणी अनुकूलता' : 'Microclimate Spray Window'}
                        </div>
                        <div className="suggestion-desc">
                          {lang === 'mr' ? 'वारा, पाऊस व उष्णतेनुसार फवारणी सुरक्षितता' : 'Real-time wind drift, wash-off, and Delta-T safety check'}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Chat Turns Stream */}
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className={`chat-turn ${msg.sender}`}>
                    {msg.sender === 'user' ? (
                      <div className="user-bubble">
                        {msg.image && (
                          <div style={{ marginBottom: '0.5rem', borderRadius: '8px', overflow: 'hidden', maxWidth: '240px' }}>
                            <img src={msg.image} alt="User leaf upload" style={{ width: '100%', display: 'block' }} />
                          </div>
                        )}
                        <p>{msg.text}</p>
                      </div>
                    ) : (
                      <div className="assistant-message-wrap">
                        <div className="assistant-avatar">
                          <Sprout size={16} />
                        </div>
                        <div className="assistant-content">
                          <p style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</p>

                          {/* Key Grounded Recommendations */}
                          {msg.recommendations?.length > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.35rem' }}>
                              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                                {lang === 'mr' ? '🌾 ICAR/CIBRC प्रमाणित उपाय:' : '🌾 Verified Recommendations:'}
                              </span>
                              {msg.recommendations.map((rec, ri) => (
                                <div key={ri} style={{
                                  background: 'var(--bg-card)',
                                  border: '1px solid var(--border-subtle)',
                                  borderLeft: '3px solid var(--accent-green)',
                                  borderRadius: '8px',
                                  padding: '0.6rem 0.85rem',
                                  fontSize: '0.84rem',
                                  color: 'var(--text-primary)',
                                  boxShadow: 'var(--shadow-sm)'
                                }}>
                                  {rec}
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Statutory Legal Disclaimer */}
                          {msg.disclaimer && (
                            <div className="statutory-callout" style={{ marginTop: '0.5rem' }}>
                              ⚖️ {msg.disclaimer}
                            </div>
                          )}

                          {/* Claude-style Artifact Trigger Card */}
                          {msg.isDiagnosticArtifact && msg.result && (
                            <div
                              className="artifact-trigger-card"
                              onClick={() => {
                                setDiagResult(msg.result);
                                setActiveArtifactOpen(true);
                              }}
                            >
                              <div className="artifact-trigger-left">
                                <div className="artifact-doc-icon">
                                  <FileText size={20} />
                                </div>
                                <div className="artifact-title-box">
                                  <h4>{msg.result.crop?.toUpperCase()}: {msg.result.predicted_class}</h4>
                                  <p>
                                    Confidence: {((msg.result.confidence || 0) * 100).toFixed(1)}% · Grad-CAM Visual Saliency & Advisory
                                  </p>
                                </div>
                              </div>
                              <div className="artifact-open-pill">
                                <span>{lang === 'mr' ? 'अहवाल उघडा' : 'View Artifact'}</span>
                                <ArrowRight size={14} />
                              </div>
                            </div>
                          )}

                          {/* Foliar Quality Guidance Callout (SRS FR-010, FR-014, ERR-001) */}
                          {msg.isQualityAlert && msg.tips && (
                            <div style={{ background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '10px', padding: '0.85rem 1rem', marginTop: '0.5rem' }}>
                              <h5 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#92400E', marginBottom: '0.35rem' }}>
                                📷 {lang === 'mr' ? 'फोटो काढण्यासाठी मार्गदर्शन:' : 'Recommended Photography Tips:'}
                              </h5>
                              <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#78350F', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                                {msg.tips.map((tip, ti) => (
                                  <li key={ti}>{tip}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Interactive Weather Card (SRS FR-021 to FR-029) */}
                          {msg.isWeatherCard && msg.weather && (
                            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '1rem', marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', boxShadow: 'var(--shadow-sm)' }}>
                              {msg.weather.spray_window && (
                                <div style={{
                                  padding: '0.75rem',
                                  borderRadius: '8px',
                                  backgroundColor: msg.weather.spray_window.status === 'optimal' ? 'var(--status-optimal-bg)' : 'var(--status-warning-bg)',
                                  color: msg.weather.spray_window.status === 'optimal' ? 'var(--status-optimal-text)' : 'var(--status-warning-text)',
                                  fontWeight: 600,
                                  fontSize: '0.85rem',
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center'
                                }}>
                                  <span>
                                    {msg.weather.spray_window.status === 'optimal' ? '✅ Optimal Spray Window: GO' : '⚠️ Spray Window Gated: CAUTION'}
                                  </span>
                                  <span style={{ fontSize: '0.75rem' }}>Delta-T: {msg.weather.spray_window.delta_t_c ? msg.weather.spray_window.delta_t_c.toFixed(1) : '--'}°C</span>
                                </div>
                              )}

                              <div className="weather-stats-grid">
                                <div style={{ background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: '6px', textAlign: 'center' }}>
                                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Temp</div>
                                  <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{msg.weather.current?.temperature_c ?? '--'}°C</div>
                                </div>
                                <div style={{ background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: '6px', textAlign: 'center' }}>
                                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Humidity</div>
                                  <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{msg.weather.current?.relative_humidity_pct ?? '--'}%</div>
                                </div>
                                <div style={{ background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: '6px', textAlign: 'center' }}>
                                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Wind</div>
                                  <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{msg.weather.current?.wind_speed_kmh ?? '--'} km/h</div>
                                </div>
                                <div style={{ background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: '6px', textAlign: 'center' }}>
                                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Rain</div>
                                  <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{msg.weather.current?.precipitation_probability_6h ?? '0'}%</div>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Source Citations */}
                          {msg.sources?.length > 0 && (
                            <div className="citations-row">
                              {msg.sources.map((s, si) => (
                                <span key={si} className="citation-chip">
                                  📚 {s.source_name || s.organization || 'ICAR'}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {/* Loading indicator */}
                {isLoading && (
                  <div className="chat-turn assistant">
                    <div className="assistant-message-wrap">
                      <div className="assistant-avatar">
                        <Sprout size={16} />
                      </div>
                      <div className="assistant-content">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          <span style={{ animation: 'spin 1.5s linear infinite' }}>⏳</span>
                          <span>{t.thinking}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={feedEndRef} />
              </div>
            </div>

            {/* Multimodal Claude Bottom Prompt Bar */}
            <InputBar
              text={inputText}
              onTextChange={setInputText}
              onSend={handleSend}
              isLoading={isLoading}
              selectedImage={selectedImage}
              imagePreview={imagePreview}
              onImageChange={handleImageChange}
              onRemoveImage={handleRemoveImage}
              crop={crop}
              onCropChange={setCrop}
              district={district}
              onDistrictChange={setDistrict}
              districtsList={districtsList}
              gpsLocation={gpsLocation}
              onUseGps={handleUseGps}
              useEdgeAi={useEdgeAi}
              onToggleEdgeAi={() => setUseEdgeAi(!useEdgeAi)}
              lang={lang}
              t={t}
            />
          </div>

          {/* Claude-Style Artifact Panel (Split View on Right) */}
          <ArtifactPanel
            isOpen={activeArtifactOpen}
            onClose={() => setActiveArtifactOpen(false)}
            diagResult={diagResult}
            imagePreview={imagePreview}
            weatherData={weatherData}
            lang={lang}
            t={t}
            onDownloadPdf={handleDownloadPdf}
            pdfDownloading={pdfDownloading}
            onOpenKvkModal={() => setShowKvkModal(true)}
          />
        </div>
      </div>

      {/* Modals */}
      <FarmModal
        isOpen={showFarmModal}
        onClose={() => setShowFarmModal(false)}
        farms={farms}
        onSaveFarm={handleSaveFarm}
        onDeleteFarm={handleDeleteFarm}
        lang={lang}
        district={district}
      />

      <KvkModal
        isOpen={showKvkModal}
        onClose={() => setShowKvkModal(false)}
        diagResult={diagResult}
        district={district}
        lang={lang}
      />

      <OfflineGuideModal
        isOpen={showOfflineGuideModal}
        onClose={() => setShowOfflineGuideModal(false)}
        lang={lang}
        t={t}
        currentCrop={crop}
      />

      <ProfileModal
        isOpen={showProfileModal}
        onClose={() => setShowProfileModal(false)}
        profile={profile}
        onSaveProfile={setProfile}
        lang={lang}
        onLangChange={setLang}
        districtsList={districtsList}
      />
    </div>
  );
}
