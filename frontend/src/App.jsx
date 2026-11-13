import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  MessageSquare, Plus, Trash2, Search, Image as ImageIcon,
  FileText, Mic, MicOff, Send, Square, Volume2, VolumeX,
  Copy, Check, RotateCcw, Edit3, Menu, X, Sparkles,
  ChevronDown, ChevronUp, CloudRain, ShieldCheck, AlertTriangle,
  Leaf, ExternalLink, RefreshCw
} from 'lucide-react';
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

const STORAGE_KEY = 'pikvaidya_conversations';
const ACTIVE_CONV_KEY = 'pikvaidya_active_conv_id';

export default function App() {
  // Locale & Core Settings
  const [lang, setLang] = useState('mr'); // Default Marathi for regional farmers
  const [selectedCrop, setSelectedCrop] = useState('auto');
  const t = translations[lang] || translations.en;

  // Conversations State
  const [conversations, setConversations] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (e) {
      console.warn('Could not parse saved conversations:', e);
    }
    return [];
  });

  const [activeConvId, setActiveConvId] = useState(() => {
    try {
      return localStorage.getItem(ACTIVE_CONV_KEY) || null;
    } catch {
      return null;
    }
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [editingTitleId, setEditingTitleId] = useState(null);
  const [tempTitle, setTempTitle] = useState('');

  // Composer State
  const [inputText, setInputText] = useState('');
  const [attachedImages, setAttachedImages] = useState([]); // [{ name, base64, preview }]
  const [attachedPdf, setAttachedPdf] = useState(null); // { name, base64 }
  const [isGenerating, setIsGenerating] = useState(false);
  const [isListening, setIsListening] = useState(false);

  // Audio / Speech State
  const [speakingMsgId, setSpeakingMsgId] = useState(null);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [copiedMsgId, setCopiedMsgId] = useState(null);

  // Network & Offline Status
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [queueStats, setQueueStats] = useState({ pendingCount: 0, failedCount: 0, totalQueued: 0 });
  const [isSyncing, setIsSyncing] = useState(false);
  const [offlineBanner, setOfflineBanner] = useState(null);
  const [deferredPrompt, setDeferredPrompt] = useState(null);

  // Grad-CAM Heatmap Viewer Modal State
  const [gradcamModal, setGradcamModal] = useState(null); // { originalImage, heatmapUrl, disease, confidence }

  // Location / Weather context
  const [gpsLocation, setGpsLocation] = useState(null);

  // Refs
  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileImageRef = useRef(null);
  const filePdfRef = useRef(null);
  const abortControllerRef = useRef(null);
  const speechSynthRef = useRef(typeof window !== 'undefined' ? window.speechSynthesis : null);

  // Save conversations to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch (e) {
      console.warn('Failed to save conversations:', e);
    }
  }, [conversations]);

  useEffect(() => {
    try {
      if (activeConvId) localStorage.setItem(ACTIVE_CONV_KEY, activeConvId);
      else localStorage.removeItem(ACTIVE_CONV_KEY);
    } catch (e) {
      console.warn('Failed to save active conversation id:', e);
    }
  }, [activeConvId]);

  // Ensure an active conversation exists
  useEffect(() => {
    if (conversations.length === 0) {
      const initialConv = createNewConversation(false);
      setConversations([initialConv]);
      setActiveConvId(initialConv.id);
    } else if (!activeConvId || !conversations.some(c => c.id === activeConvId)) {
      setActiveConvId(conversations[0].id);
    }
  }, [conversations, activeConvId]);

  // Network & Sync queue listeners
  useEffect(() => {
    const unsubNet = syncManager.addNetworkListener((online) => {
      setIsOnline(online);
      refreshQueue();
    });

    const unsubSync = syncManager.addSyncListener((res) => {
      refreshQueue();
      if (res.syncedCount > 0) {
        setOfflineBanner(`✅ ${res.syncedCount} offline scans synchronized successfully!`);
        setTimeout(() => setOfflineBanner(null), 5000);
      }
    });

    refreshQueue();

    // Acquire GPS silently if permitted
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setGpsLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => console.log('Location permission not granted or silent timeout')
      );
    }

    // PWA Prompt
    const handleBeforeInstall = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };
    window.addEventListener('beforeinstallprompt', handleBeforeInstall);

    return () => {
      unsubNet();
      unsubSync();
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
    };
  }, []);

  const refreshQueue = async () => {
    try {
      const stats = await getSyncQueueStats();
      setQueueStats(stats);
    } catch (e) {
      console.warn('Could not read offline queue stats:', e);
    }
  };

  const handleManualSync = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    await syncManager.syncNow();
    await refreshQueue();
    setIsSyncing(false);
  };

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') setDeferredPrompt(null);
  };

  // Scroll to bottom on new messages
  const activeConversation = useMemo(() => {
    return conversations.find(c => c.id === activeConvId) || conversations[0] || null;
  }, [conversations, activeConvId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConversation?.messages?.length, activeConversation?.messages?.[activeConversation?.messages?.length - 1]?.text]);

  // Auto-resize composer textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [inputText]);

  // Create new conversation helper
  const createNewConversation = (makeActive = true) => {
    const newId = `conv-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
    const newConv = {
      id: newId,
      title: lang === 'mr' ? 'नवीन संवाद' : (lang === 'hi' ? 'नई बातचीत' : 'New Consultation'),
      crop: selectedCrop,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      messages: []
    };
    if (makeActive) {
      setConversations(prev => [newConv, ...prev]);
      setActiveConvId(newId);
      setInputText('');
      setAttachedImages([]);
      setAttachedPdf(null);
      if (window.innerWidth <= 768) setSidebarOpen(false);
    }
    return newConv;
  };

  // Delete conversation
  const handleDeleteConversation = (id, e) => {
    e.stopPropagation();
    if (window.confirm(t.deleteChatConfirm)) {
      setConversations(prev => {
        const remaining = prev.filter(c => c.id !== id);
        if (id === activeConvId) {
          const nextActive = remaining[0]?.id || null;
          setActiveConvId(nextActive);
        }
        return remaining;
      });
    }
  };

  // Clear all conversations
  const handleClearAll = () => {
    if (window.confirm(t.clearAllConfirm)) {
      setConversations([]);
      setActiveConvId(null);
    }
  };

  // Conversation title edit
  const handleStartRename = (conv, e) => {
    e.stopPropagation();
    setEditingTitleId(conv.id);
    setTempTitle(conv.title);
  };

  const handleSaveRename = (id) => {
    if (tempTitle.trim()) {
      setConversations(prev => prev.map(c => c.id === id ? { ...c, title: tempTitle.trim() } : c));
    }
    setEditingTitleId(null);
  };

  // Filtered & Grouped conversations
  const groupedConversations = useMemo(() => {
    const filtered = conversations.filter(c => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      if (c.title?.toLowerCase().includes(q)) return true;
      return c.messages?.some(m => m.text?.toLowerCase().includes(q));
    });

    const now = Date.now();
    const oneDay = 24 * 60 * 60 * 1000;
    const groups = {
      today: [],
      yesterday: [],
      previous7Days: [],
      older: []
    };

    filtered.forEach(conv => {
      const diff = now - conv.updatedAt;
      if (diff < oneDay) {
        groups.today.push(conv);
      } else if (diff < 2 * oneDay) {
        groups.yesterday.push(conv);
      } else if (diff < 7 * oneDay) {
        groups.previous7Days.push(conv);
      } else {
        groups.older.push(conv);
      }
    });

    return groups;
  }, [conversations, searchQuery]);

  // Image attachments handler (Multi-image)
  const handleImageSelect = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        const b64 = reader.result.split(',')[1];
        setAttachedImages(prev => [
          ...prev,
          { name: file.name, base64: b64, preview: reader.result }
        ]);
      };
      reader.readAsDataURL(file);
    });
    e.target.value = '';
  };

  const removeImage = (index) => {
    setAttachedImages(prev => prev.filter((_, i) => i !== index));
  };

  // PDF attachment handler
  const handlePdfSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const b64 = reader.result.split(',')[1];
      setAttachedPdf({ name: file.name, base64: b64 });
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const removePdf = () => {
    setAttachedPdf(null);
  };

  // Voice speech-to-text
  const toggleVoice = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert(lang === 'mr' ? 'आपल्या ब्राउझरमध्ये व्हॉइस इनपुट उपलब्ध नाही.' : 'Voice recognition is not supported in this browser.');
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = lang === 'mr' ? 'mr-IN' : (lang === 'hi' ? 'hi-IN' : 'en-IN');
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);
    recognition.onresult = (event) => {
      const speechText = event.results[0][0].transcript;
      setInputText(prev => (prev ? prev + ' ' + speechText : speechText));
    };
    recognition.start();
  };

  // Text-to-Speech (TTS)
  const toggleSpeakMessage = (msgId, text) => {
    if (!speechSynthRef.current) return;

    if (speakingMsgId === msgId) {
      speechSynthRef.current.cancel();
      setSpeakingMsgId(null);
      return;
    }

    speechSynthRef.current.cancel();
    const cleanText = text.replace(/[*#_`~]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = lang === 'mr' ? 'mr-IN' : (lang === 'hi' ? 'hi-IN' : 'en-US');
    utterance.rate = 0.95;

    utterance.onend = () => setSpeakingMsgId(null);
    utterance.onerror = () => setSpeakingMsgId(null);

    setSpeakingMsgId(msgId);
    speechSynthRef.current.speak(utterance);
  };

  // Copy message text
  const handleCopyText = (msgId, text) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(msgId);
    setTimeout(() => setCopiedMsgId(null), 2000);
  };

  // Stop Generation
  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsGenerating(false);
  };

  // Edit user message (loads back into composer)
  const handleEditMessage = (msg) => {
    setInputText(msg.text || '');
    if (msg.images?.length) setAttachedImages(msg.images);
    if (msg.pdf) setAttachedPdf(msg.pdf);
    textareaRef.current?.focus();
  };

  // Core Send / Streaming Message Handler
  const handleSendMessage = async (textOverride = null) => {
    const textToSend = (textOverride !== null ? textOverride : inputText).trim();
    if ((!textToSend && !attachedImages.length && !attachedPdf) || isGenerating) return;

    // Snapshot attachments and reset inputs
    const currentImages = [...attachedImages];
    const currentPdf = attachedPdf;
    setInputText('');
    setAttachedImages([]);
    setAttachedPdf(null);

    let convId = activeConvId;
    let targetConv = conversations.find(c => c.id === convId);

    if (!targetConv) {
      targetConv = createNewConversation(true);
      convId = targetConv.id;
    }

    const userMsgId = `msg-user-${Date.now()}`;
    const botMsgId = `msg-bot-${Date.now()}`;

    const userMsg = {
      id: userMsgId,
      sender: 'user',
      text: textToSend,
      images: currentImages,
      pdf: currentPdf,
      timestamp: Date.now()
    };

    const initialBotMsg = {
      id: botMsgId,
      sender: 'bot',
      text: '',
      isStreaming: true,
      tools: [],
      diagnostic: null,
      diagnostic_results: [],
      weather: null,
      sources: [],
      recommendations: [],
      timestamp: Date.now()
    };

    // Auto-update conversation title from first question
    const updatedTitle = targetConv.messages.length === 0
      ? (textToSend ? textToSend.slice(0, 38) + (textToSend.length > 38 ? '...' : '') : (currentImages[0]?.name || 'Foliar Diagnosis'))
      : targetConv.title;

    setConversations(prev => prev.map(c => {
      if (c.id === convId) {
        return {
          ...c,
          title: updatedTitle,
          updatedAt: Date.now(),
          messages: [...c.messages, userMsg, initialBotMsg]
        };
      }
      return c;
    }));

    setIsGenerating(true);
    abortControllerRef.current = new AbortController();

    // -------------------------------------------------------------------------
    // Offline-First Branch: If browser is offline, route to Local Edge AI
    // -------------------------------------------------------------------------
    if (typeof navigator !== 'undefined' && (!navigator.onLine || !isOnline)) {
      try {
        let edgeReply = '';
        let edgeDiagnostic = null;

        if (currentImages.length > 0) {
          const targetCrop = selectedCrop === 'auto' ? 'sugarcane' : selectedCrop;
          const edgeRes = await runLocalEdgeInference(targetCrop, currentImages[0].preview);

          await queueOfflineDiagnosis({
            image_data: currentImages[0].preview,
            image_name: currentImages[0].name,
            crop: targetCrop,
            district: 'pune',
            latitude: gpsLocation?.lat || null,
            longitude: gpsLocation?.lon || null,
            captured_at: new Date().toISOString(),
            client_preview: edgeRes,
            is_local_inference: true
          });
          await refreshQueue();

          edgeDiagnostic = {
            crop: targetCrop,
            predicted_class: edgeRes.predicted_disease,
            confidence: edgeRes.confidence,
            confidence_percentage: edgeRes.confidence_percentage,
            is_local_inference: true,
            model_version: `MobileNetV3 INT8 Edge WASM (${edgeRes.inference_time_ms}ms)`,
            details: { severity: 'LOCAL_ANALYSIS', offline_queued: true }
          };

          edgeReply = lang === 'mr'
            ? `[डिव्हाइसवरील जलद AI निदान] ${edgeRes.predicted_disease} आढळले (विश्वासार्हता: ${edgeRes.confidence_percentage}%).\n\nइंटरनेट सुरू होताच हे स्कॅन क्लाउडवर स्वयंचलित सिंक होईल आणि पूर्ण सविस्तर अहवाल उपलब्ध होईल.`
            : `[On-Device Edge AI Diagnosis] Identified: ${edgeRes.predicted_disease} (${edgeRes.confidence_percentage}% confidence).\n\nThis leaf scan is queued in IndexedDB and will synchronize automatically when internet is available.`;
        } else {
          const localChunks = await searchOfflineKnowledge(selectedCrop !== 'auto' ? selectedCrop : null, textToSend, lang);
          if (localChunks.length > 0) {
            edgeReply = (lang === 'mr' ? `[ऑफलाइन माहिती]\n` : `[Offline Knowledge]\n`) + localChunks[0].text;
          } else {
            edgeReply = lang === 'mr'
              ? 'सध्या तुम्ही ऑफलाइन आहात. संपूर्ण AI उत्तरासाठी कृपया इंटरनेट चालू करा.'
              : 'You are currently offline. Full conversational responses require internet connectivity.';
          }
        }

        setConversations(prev => prev.map(c => {
          if (c.id === convId) {
            return {
              ...c,
              messages: c.messages.map(m => m.id === botMsgId ? {
                ...m,
                text: edgeReply,
                isStreaming: false,
                diagnostic: edgeDiagnostic,
                tools: [{ tool_name: 'Edge AI WASM', input_params: {}, output_summary: 'On-device diagnosis', execution_status: 'SUCCESS' }]
              } : m)
            };
          }
          return c;
        }));
      } catch (err) {
        setConversations(prev => prev.map(c => {
          if (c.id === convId) {
            return {
              ...c,
              messages: c.messages.map(m => m.id === botMsgId ? {
                ...m,
                text: `Offline Error: ${err.message}`,
                isStreaming: false
              } : m)
            };
          }
          return c;
        }));
      } finally {
        setIsGenerating(false);
      }
      return;
    }

    // -------------------------------------------------------------------------
    // Online Conversational Streaming (Server-Sent Events)
    // -------------------------------------------------------------------------
    try {
      const payload = {
        message: textToSend,
        language: lang,
        session_id: convId,
        crop: selectedCrop !== 'auto' ? selectedCrop : 'sugarcane',
        image_base64: currentImages[0]?.base64 || null,
        images_base64: currentImages.map(img => img.base64),
        image_filename: currentImages[0]?.name || null,
        pdf_base64: currentPdf?.base64 || null,
        pdf_filename: currentPdf?.name || null,
        latitude: gpsLocation?.lat || null,
        longitude: gpsLocation?.lon || null,
      };

      const response = await fetch('/api/v1/assistant/chat-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        // Fallback to standard multimodal endpoint if stream fails
        const fallbackRes = await fetch('/api/v1/assistant/multimodal-chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: abortControllerRef.current.signal
        });
        const fallbackData = await fallbackRes.json();

        setConversations(prev => prev.map(c => {
          if (c.id === convId) {
            return {
              ...c,
              messages: c.messages.map(m => m.id === botMsgId ? {
                ...m,
                text: fallbackData.reply || fallbackData.answer || 'Response generated.',
                isStreaming: false,
                tools: fallbackData.tools_invoked || [],
                diagnostic: fallbackData.diagnostic_result,
                diagnostic_results: fallbackData.diagnostic_results || [],
                weather: fallbackData.weather_result,
                sources: fallbackData.sources || fallbackData.retrieved_sources || [],
                recommendations: fallbackData.key_recommendations || []
              } : m)
            };
          }
          return c;
        }));

        if (autoSpeak) toggleSpeakMessage(botMsgId, fallbackData.reply || fallbackData.answer || '');
        return;
      }

      // Read SSE Stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let accumulatedText = '';
      let accumulatedTools = [];
      let finalDiagnostic = null;
      let finalDiagnosticResults = [];
      let finalWeather = null;
      let finalSources = [];
      let finalRecommendations = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          const eventLine = block.split('\n').find(l => l.startsWith('event: '));
          const dataLine = block.split('\n').find(l => l.startsWith('data: '));

          if (!dataLine) continue;
          const eventType = eventLine ? eventLine.replace('event: ', '').trim() : 'message';
          const eventData = JSON.parse(dataLine.replace('data: ', '').trim());

          if (eventType === 'token') {
            accumulatedText += eventData.token;
            setConversations(prev => prev.map(c => {
              if (c.id === convId) {
                return {
                  ...c,
                  messages: c.messages.map(m => m.id === botMsgId ? { ...m, text: accumulatedText } : m)
                };
              }
              return c;
            }));
          } else if (eventType === 'tool') {
            accumulatedTools.push(eventData);
            setConversations(prev => prev.map(c => {
              if (c.id === convId) {
                return {
                  ...c,
                  messages: c.messages.map(m => m.id === botMsgId ? { ...m, tools: [...accumulatedTools] } : m)
                };
              }
              return c;
            }));
          } else if (eventType === 'done') {
            finalDiagnostic = eventData.diagnostic_result;
            finalDiagnosticResults = eventData.diagnostic_results || [];
            finalWeather = eventData.weather_result;
            finalSources = eventData.sources || [];
            finalRecommendations = eventData.key_recommendations || [];
          }
        }
      }

      // Mark streaming complete
      setConversations(prev => prev.map(c => {
        if (c.id === convId) {
          return {
            ...c,
            messages: c.messages.map(m => m.id === botMsgId ? {
              ...m,
              isStreaming: false,
              text: accumulatedText || 'Consultation complete.',
              diagnostic: finalDiagnostic,
              diagnostic_results: finalDiagnosticResults,
              weather: finalWeather,
              sources: finalSources,
              recommendations: finalRecommendations
            } : m)
          };
        }
        return c;
      }));

      if (autoSpeak && accumulatedText) {
        toggleSpeakMessage(botMsgId, accumulatedText);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('User stopped generation');
      } else {
        setConversations(prev => prev.map(c => {
          if (c.id === convId) {
            return {
              ...c,
              messages: c.messages.map(m => m.id === botMsgId ? {
                ...m,
                isStreaming: false,
                text: `Connection error: ${err.message}. Please verify backend status.`
              } : m)
            };
          }
          return c;
        }));
      }
    } finally {
      setIsGenerating(false);
      abortControllerRef.current = null;
    }
  };

  // Regenerate Response
  const handleRegenerate = () => {
    if (!activeConversation || isGenerating) return;
    const msgs = activeConversation.messages;
    const lastUserMsg = [...msgs].reverse().find(m => m.sender === 'user');
    if (!lastUserMsg) return;

    // Remove the trailing bot message if any
    setConversations(prev => prev.map(c => {
      if (c.id === activeConvId) {
        const trimmed = c.messages[c.messages.length - 1]?.sender === 'bot'
          ? c.messages.slice(0, -1)
          : c.messages;
        return { ...c, messages: trimmed };
      }
      return c;
    }));

    handleSendMessage(lastUserMsg.text);
  };

  return (
    <div className="chat-app-root">
      {/* Offline sync banner */}
      {offlineBanner && (
        <div className="offline-toast">
          <span>{offlineBanner}</span>
          <button onClick={() => setOfflineBanner(null)}>✕</button>
        </div>
      )}

      {/* Main Container */}
      <div className="chat-layout">
        {/* ================================================================= */}
        {/* SIDEBAR: History & Conversation Management                       */}
        {/* ================================================================= */}
        <aside className={`chat-sidebar ${sidebarOpen ? 'open' : ''}`}>
          {/* Brand & New Chat */}
          <div className="sidebar-header">
            <div className="sidebar-brand">
              <span className="brand-logo">🌿</span>
              <div className="brand-info">
                <h2>{t.appTitle}</h2>
                <span className="brand-tag">{t.appSubtitle}</span>
              </div>
            </div>
            <button
              className="new-chat-btn"
              onClick={() => createNewConversation(true)}
              title={t.newChat}
            >
              <Plus size={18} />
              <span>{t.newChat}</span>
            </button>
          </div>

          {/* Search Bar */}
          <div className="sidebar-search">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder={t.searchChats}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="clear-search" onClick={() => setSearchQuery('')}>✕</button>
            )}
          </div>

          {/* Conversations List Grouped */}
          <div className="sidebar-conversations">
            {conversations.length === 0 ? (
              <div className="no-chats-msg">{t.noChatsFound}</div>
            ) : (
              <>
                {groupedConversations.today.length > 0 && (
                  <div className="conv-group">
                    <span className="group-title">{t.today}</span>
                    {groupedConversations.today.map(c => renderConvItem(c))}
                  </div>
                )}

                {groupedConversations.yesterday.length > 0 && (
                  <div className="conv-group">
                    <span className="group-title">{t.yesterday}</span>
                    {groupedConversations.yesterday.map(c => renderConvItem(c))}
                  </div>
                )}

                {groupedConversations.previous7Days.length > 0 && (
                  <div className="conv-group">
                    <span className="group-title">{t.previous7Days}</span>
                    {groupedConversations.previous7Days.map(c => renderConvItem(c))}
                  </div>
                )}

                {groupedConversations.older.length > 0 && (
                  <div className="conv-group">
                    <span className="group-title">{t.older}</span>
                    {groupedConversations.older.map(c => renderConvItem(c))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Sidebar Footer */}
          <div className="sidebar-footer">
            <div className="footer-status">
              <span className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
              <span className="status-label">
                {isOnline ? t.onlineStatus : t.offlineStatus}
              </span>
              {queueStats.pendingCount > 0 && (
                <button
                  className="sync-pill"
                  onClick={handleManualSync}
                  disabled={isSyncing}
                  title={t.syncNow}
                >
                  <RefreshCw size={12} className={isSyncing ? 'spinning' : ''} />
                  <span>{queueStats.pendingCount}</span>
                </button>
              )}
            </div>

            {deferredPrompt && (
              <button className="pwa-install-btn" onClick={handleInstallClick}>
                <Leaf size={14} />
                <span>{t.installApp}</span>
              </button>
            )}

            <button className="clear-all-btn" onClick={handleClearAll} title={t.clearAllChats}>
              <Trash2 size={14} />
              <span>{t.clearAllChats}</span>
            </button>
          </div>
        </aside>

        {/* Sidebar Overlay on mobile */}
        {sidebarOpen && (
          <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />
        )}

        {/* ================================================================= */}
        {/* MAIN CHAT AREA                                                    */}
        {/* ================================================================= */}
        <main className="chat-main">
          {/* Top Navbar */}
          <header className="chat-header">
            <div className="header-left">
              <button
                className="hamburger-btn"
                onClick={() => setSidebarOpen(prev => !prev)}
                title="Toggle Sidebar"
              >
                <Menu size={20} />
              </button>
              <div className="active-conv-title">
                {activeConversation?.title || t.appTitle}
              </div>
            </div>

            <div className="header-right">
              {/* Target Crop Selector */}
              <div className="header-crop-picker">
                <select
                  value={selectedCrop}
                  onChange={(e) => setSelectedCrop(e.target.value)}
                  className="crop-dropdown"
                >
                  <option value="auto">🌿 {t.autoDetect}</option>
                  <option value="sugarcane">🎋 {t.sugarcane}</option>
                  <option value="tomato">🍅 {t.tomato}</option>
                  <option value="onion">🧅 {t.onion}</option>
                </select>
              </div>

              {/* Language Selector */}
              <div className="lang-switcher">
                <button
                  className={`lang-btn ${lang === 'mr' ? 'active' : ''}`}
                  onClick={() => setLang('mr')}
                >
                  मराठी
                </button>
                <button
                  className={`lang-btn ${lang === 'hi' ? 'active' : ''}`}
                  onClick={() => setLang('hi')}
                >
                  हिंदी
                </button>
                <button
                  className={`lang-btn ${lang === 'en' ? 'active' : ''}`}
                  onClick={() => setLang('en')}
                >
                  EN
                </button>
              </div>

              {/* Auto Voice Toggle */}
              <button
                className={`voice-toggle-btn ${autoSpeak ? 'active' : ''}`}
                onClick={() => setAutoSpeak(prev => !prev)}
                title={autoSpeak ? t.stopReading : t.readAloud}
              >
                {autoSpeak ? <Volume2 size={18} /> : <VolumeX size={18} />}
              </button>
            </div>
          </header>

          {/* Messages Scroll Area */}
          <div className="chat-messages-container">
            {(!activeConversation || activeConversation.messages.length === 0) ? (
              /* Empty State / Welcome Screen */
              <div className="welcome-screen">
                <div className="welcome-emblem">🌿</div>
                <h2>{t.appTitle}</h2>
                <p className="welcome-sub">{t.appSubtitle}</p>

                <div className="quick-questions-grid">
                  {t.quickQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      className="quick-q-card"
                      onClick={() => handleSendMessage(q)}
                    >
                      <Sparkles size={16} className="sparkle-icon" />
                      <span>{q}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Message Thread */
              <div className="messages-thread">
                {activeConversation.messages.map((msg) => renderMessage(msg))}
                <div ref={chatEndRef} />
              </div>
            )}
          </div>

          {/* =============================================================== */}
          {/* COMPOSER / INPUT TRAY                                           */}
          {/* =============================================================== */}
          <footer className="chat-composer-section">
            {/* Attachment Previews Tray */}
            {(attachedImages.length > 0 || attachedPdf) && (
              <div className="attachment-tray">
                {attachedImages.map((img, idx) => (
                  <div key={idx} className="preview-chip image-chip">
                    <img src={img.preview} alt="Attachment" />
                    <span className="file-name">{img.name}</span>
                    <button onClick={() => removeImage(idx)} title="Remove">✕</button>
                  </div>
                ))}

                {attachedPdf && (
                  <div className="preview-chip pdf-chip">
                    <FileText size={18} />
                    <span className="file-name">{attachedPdf.name}</span>
                    <button onClick={removePdf} title="Remove">✕</button>
                  </div>
                )}
              </div>
            )}

            {/* Composer Input Bar */}
            <div className="composer-bar">
              {/* Left Action Buttons */}
              <div className="composer-actions-left">
                <button
                  type="button"
                  className="attach-btn"
                  onClick={() => fileImageRef.current?.click()}
                  title={t.uploadImages}
                >
                  <ImageIcon size={20} />
                </button>
                <input
                  type="file"
                  ref={fileImageRef}
                  style={{ display: 'none' }}
                  multiple
                  accept="image/*"
                  onChange={handleImageSelect}
                />

                <button
                  type="button"
                  className="attach-btn"
                  onClick={() => filePdfRef.current?.click()}
                  title={t.uploadPdf}
                >
                  <FileText size={20} />
                </button>
                <input
                  type="file"
                  ref={filePdfRef}
                  style={{ display: 'none' }}
                  accept="application/pdf"
                  onChange={handlePdfSelect}
                />
              </div>

              {/* Textarea */}
              <textarea
                ref={textareaRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder={isListening ? t.voiceListening : t.chatPlaceholder}
                rows={1}
                className="composer-textarea"
              />

              {/* Right Action Buttons */}
              <div className="composer-actions-right">
                {/* Voice Recognition */}
                <button
                  type="button"
                  className={`voice-mic-btn ${isListening ? 'listening' : ''}`}
                  onClick={toggleVoice}
                  title={t.voiceInput}
                >
                  {isListening ? <MicOff size={20} /> : <Mic size={20} />}
                </button>

                {/* Stop Generation OR Send Button */}
                {isGenerating ? (
                  <button
                    type="button"
                    className="stop-btn"
                    onClick={handleStopGeneration}
                    title={t.stopGenerating}
                  >
                    <Square size={16} fill="currentColor" />
                  </button>
                ) : (
                  <button
                    type="button"
                    className={`send-btn ${(inputText.trim() || attachedImages.length || attachedPdf) ? 'active' : ''}`}
                    onClick={() => handleSendMessage()}
                    disabled={!inputText.trim() && !attachedImages.length && !attachedPdf}
                    title="Send"
                  >
                    <Send size={18} />
                  </button>
                )}
              </div>
            </div>

            <div className="composer-disclaimer">
              <span>🌿 PikVaidya AI autonomously integrates ICAR/CIBRC guidance, foliar vision & microclimate telemetry.</span>
            </div>
          </footer>
        </main>
      </div>

      {/* =================================================================== */}
      {/* GRAD-CAM HEATMAP MODAL                                             */}
      {/* =================================================================== */}
      {gradcamModal && (
        <div className="gradcam-modal-backdrop" onClick={() => setGradcamModal(null)}>
          <div className="gradcam-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>🔍 {gradcamModal.disease} ({Math.round(gradcamModal.confidence * 100)}%)</h3>
              <button className="close-btn" onClick={() => setGradcamModal(null)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="heatmap-comparison">
                {gradcamModal.originalImage && (
                  <div className="leaf-side">
                    <h4>Original Leaf Sample</h4>
                    <img src={gradcamModal.originalImage} alt="Original Sample" />
                  </div>
                )}
                <div className="heatmap-side">
                  <h4>Grad-CAM Visual Attention (XAI)</h4>
                  <img src={gradcamModal.heatmapUrl} alt="Grad-CAM Heatmap" />
                  <p className="heatmap-expl">
                    Highlighted reddish/yellow pixels indicate where the deep convolutional model detected primary pathological lesions.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  // =========================================================================
  // SUB-RENDERERS
  // =========================================================================

  // Render individual conversation item in sidebar
  function renderConvItem(conv) {
    const isActive = conv.id === activeConvId;
    const isEditing = conv.id === editingTitleId;

    return (
      <div
        key={conv.id}
        className={`conv-item ${isActive ? 'active' : ''}`}
        onClick={() => {
          setActiveConvId(conv.id);
          if (window.innerWidth <= 768) setSidebarOpen(false);
        }}
      >
        <MessageSquare size={16} className="conv-icon" />
        {isEditing ? (
          <input
            type="text"
            className="rename-input"
            value={tempTitle}
            onChange={(e) => setTempTitle(e.target.value)}
            onBlur={() => handleSaveRename(conv.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSaveRename(conv.id);
              if (e.key === 'Escape') setEditingTitleId(null);
            }}
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="conv-title">{conv.title}</span>
        )}

        <div className="conv-actions">
          <button
            className="conv-action-btn"
            onClick={(e) => handleStartRename(conv, e)}
            title="Rename"
          >
            <Edit3 size={13} />
          </button>
          <button
            className="conv-action-btn delete"
            onClick={(e) => handleDeleteConversation(conv.id, e)}
            title="Delete"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
    );
  }

  // Render message bubble
  function renderMessage(msg) {
    const isUser = msg.sender === 'user';

    return (
      <div key={msg.id} className={`message-row ${isUser ? 'user' : 'bot'}`}>
        <div className="message-avatar">
          {isUser ? '🧑‍🌾' : '🌿'}
        </div>

        <div className="message-content-wrapper">
          {/* User Attached Images */}
          {isUser && msg.images?.length > 0 && (
            <div className="user-attached-grid">
              {msg.images.map((img, i) => (
                <div key={i} className="attached-img-wrap">
                  <img src={img.preview} alt="Attached crop" />
                </div>
              ))}
            </div>
          )}

          {/* User Attached PDF */}
          {isUser && msg.pdf && (
            <div className="user-pdf-pill">
              <FileText size={16} />
              <span>{msg.pdf.name}</span>
            </div>
          )}

          {/* Main Bubble */}
          <div className={`message-bubble ${isUser ? 'user' : 'bot'}`}>
            {/* Tool Executions Accordion for Bot */}
            {!isUser && msg.tools?.length > 0 && (
              <div className="bot-tools-bar">
                <span className="tools-label">⚡ {t.toolsUsed}:</span>
                <div className="tools-pills-list">
                  {msg.tools.map((tl, idx) => (
                    <span key={idx} className="tool-pill">
                      {tl.tool_name === 'Crop Disease Diagnosis' && '🔬 Disease Classifier'}
                      {tl.tool_name === 'Microclimate & Weather Risk' && '🌦️ Weather Telemetry'}
                      {tl.tool_name === 'Agricultural RAG Knowledge' && '📚 ICAR RAG Grounding'}
                      {tl.tool_name === 'Document Analysis' && '📄 PDF Extractor'}
                      {tl.tool_name === 'Edge AI WASM' && '⚡ Local INT8 Edge AI'}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Structured Diagnostic Card if disease recognized */}
            {!isUser && msg.diagnostic && (
              <div className="diagnostic-summary-card">
                <div className="diag-header">
                  <ShieldCheck size={18} className="diag-shield" />
                  <h4>{msg.diagnostic.predicted_class}</h4>
                  <span className="diag-confidence">
                    {Math.round((msg.diagnostic.confidence || 0) * 100)}% Match
                  </span>
                </div>

                <div className="diag-meta-row">
                  <span>🌾 {msg.diagnostic.crop?.toUpperCase()}</span>
                  <span>⚙️ {msg.diagnostic.model_version || 'PyTorch Cloud'}</span>
                  {msg.diagnostic.heatmap_path && (
                    <button
                      className="view-gradcam-btn"
                      onClick={() => setGradcamModal({
                        originalImage: msg.diagnostic.image_path || null,
                        heatmapUrl: msg.diagnostic.heatmap_path,
                        disease: msg.diagnostic.predicted_class,
                        confidence: msg.diagnostic.confidence
                      })}
                    >
                      <Sparkles size={14} />
                      <span>{t.viewGradcam}</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Structured Weather Card if weather retrieved */}
            {!isUser && msg.weather && (
              <div className="weather-summary-card">
                <div className="weather-hdr">
                  <CloudRain size={16} />
                  <span>{t.weatherSpraySafety}</span>
                  <span className={`spray-badge ${msg.weather.spray_window?.summary?.status?.toLowerCase() || 'optimal'}`}>
                    {msg.weather.spray_window?.summary?.status || 'OPTIMAL'}
                  </span>
                </div>
                <div className="weather-stats">
                  <span>🌡️ {msg.weather.current?.temperature_2m}°C</span>
                  <span>💧 {msg.weather.current?.relative_humidity_2m}%</span>
                  <span>💨 {msg.weather.current?.wind_speed_10m} km/h</span>
                </div>
              </div>
            )}

            {/* Text Content */}
            <div className="message-text">
              {msg.text ? (
                <div className="formatted-text">
                  {msg.text.split('\n').map((line, idx) => (
                    <p key={idx}>{line}</p>
                  ))}
                </div>
              ) : (
                msg.isStreaming && <span className="typing-cursor">▋</span>
              )}
            </div>

            {/* Knowledge Sources Citations */}
            {!isUser && msg.sources?.length > 0 && (
              <div className="sources-container">
                <span className="sources-title">📚 {t.sourcesGrounding}:</span>
                <div className="sources-list">
                  {msg.sources.map((s, idx) => (
                    <span key={idx} className="source-tag">
                      {s.source_name || s.crop || 'ICAR Bulletin'}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Action Toolbar */}
          <div className="message-toolbar">
            <button
              className="msg-tool-btn"
              onClick={() => handleCopyText(msg.id, msg.text)}
              title={t.copy}
            >
              {copiedMsgId === msg.id ? <Check size={14} className="copied-icon" /> : <Copy size={14} />}
              {copiedMsgId === msg.id && <span className="copied-text">{t.copied}</span>}
            </button>

            <button
              className="msg-tool-btn"
              onClick={() => toggleSpeakMessage(msg.id, msg.text)}
              title={speakingMsgId === msg.id ? t.stopReading : t.readAloud}
            >
              {speakingMsgId === msg.id ? <VolumeX size={14} /> : <Volume2 size={14} />}
            </button>

            {isUser && (
              <button
                className="msg-tool-btn"
                onClick={() => handleEditMessage(msg)}
                title={t.editMessage}
              >
                <Edit3 size={14} />
              </button>
            )}

            {!isUser && !msg.isStreaming && (
              <button
                className="msg-tool-btn"
                onClick={handleRegenerate}
                title={t.regenerate}
              >
                <RotateCcw size={14} />
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }
}
