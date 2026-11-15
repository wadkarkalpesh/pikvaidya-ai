/**
 * PikVaidya AI — Indic Voice Assistant Utility
 * ============================================
 * Provides Speech-to-Text (STT) and Text-to-Speech (TTS)
 * tailored for Marathi (mr-IN), Hindi (hi-IN), and Indian English (en-IN).
 */

// 1. Language code mapping
export const getLangLocale = (lang) => {
  switch (lang) {
    case 'mr':
      return 'mr-IN';
    case 'hi':
      return 'hi-IN';
    case 'en':
    default:
      return 'en-IN';
  }
};

// 2. Check browser Speech Recognition support
export const isSpeechRecognitionSupported = () => {
  if (typeof window === 'undefined') return false;
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
};

// 3. Speech Recognizer Factory
export class IndicSpeechRecognizer {
  constructor({ onResult, onStart, onEnd, onError, lang = 'mr' }) {
    this.onResult = onResult;
    this.onStart = onStart;
    this.onEnd = onEnd;
    this.onError = onError;
    this.lang = lang;
    this.recognition = null;
    this.isListening = false;
    this.manualStop = false;
  }

  start() {
    if (!isSpeechRecognitionSupported()) {
      if (this.onError) {
        this.onError(new Error('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Android Browser.'));
      }
      return false;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();
    this.recognition.lang = getLangLocale(this.lang);
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 1;
    this.manualStop = false;

    this.recognition.onstart = () => {
      this.isListening = true;
      if (this.onStart) this.onStart();
    };

    this.recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      if (this.onResult) {
        this.onResult({
          finalTranscript: finalTranscript.trim(),
          interimTranscript: interimTranscript.trim(),
        });
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('[PikVaidya Voice] Speech recognition event error:', event.error);
      if (this.onError) this.onError(event);
    };

    this.recognition.onend = () => {
      this.isListening = false;
      if (!this.manualStop) {
        // Auto-end callback
        if (this.onEnd) this.onEnd();
      } else {
        if (this.onEnd) this.onEnd();
      }
    };

    try {
      this.recognition.start();
      return true;
    } catch (err) {
      console.error('[PikVaidya Voice] Failed to start speech recognition:', err);
      if (this.onError) this.onError(err);
      return false;
    }
  }

  stop() {
    this.manualStop = true;
    this.isListening = false;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {
        // Ignore stop error if already stopped
      }
    }
  }

  setLanguage(newLang) {
    this.lang = newLang;
    if (this.recognition) {
      this.recognition.lang = getLangLocale(newLang);
    }
  }
}

// 4. Clean Markdown formatting for natural TTS speech
export const cleanTextForSpeech = (text) => {
  if (!text) return '';
  return text
    .replace(/[*#_~`>]/g, '') // remove markdown symbols
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // link labels only
    .replace(/https?:\/\/\S+/g, '') // remove URLs
    .replace(/[🌾🌱🧅🍅🌦️⚖️📷⚡☁️🛡️📌💡🔬🚨✔️⚠️]/g, '') // remove emojis
    .replace(/\s+/g, ' ')
    .trim();
};

// 5. Text-To-Speech (Speech Synthesis) Engine
let currentUtterance = null;

export const speakAgronomicText = (text, { lang = 'mr', onStart, onEnd, onError } = {}) => {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    if (onError) onError(new Error('Speech synthesis is not supported on this device.'));
    return false;
  }

  // Cancel any ongoing speech
  stopAgronomicSpeech();

  const cleanText = cleanTextForSpeech(text);
  if (!cleanText) return false;

  const utterance = new SpeechSynthesisUtterance(cleanText);
  currentUtterance = utterance;

  const targetLocale = getLangLocale(lang);
  utterance.lang = targetLocale;
  utterance.rate = 0.93; // slightly slower for agronomic clarity
  utterance.pitch = 1.0;

  // Select the best Indic voice available
  const voices = window.speechSynthesis.getVoices();
  let bestVoice = voices.find((v) => v.lang === targetLocale || v.lang.startsWith(targetLocale));

  // If Marathi voice is not installed, fallback to Hindi voice for Devanagari text
  if (!bestVoice && lang === 'mr') {
    bestVoice = voices.find((v) => v.lang === 'hi-IN' || v.lang.startsWith('hi') || v.name.toLowerCase().includes('hindi') || v.name.toLowerCase().includes('india'));
  }

  if (bestVoice) {
    utterance.voice = bestVoice;
  }

  utterance.onstart = () => {
    if (onStart) onStart();
  };

  utterance.onend = () => {
    currentUtterance = null;
    if (onEnd) onEnd();
  };

  utterance.onerror = (e) => {
    currentUtterance = null;
    if (onError) onError(e);
  };

  window.speechSynthesis.speak(utterance);
  return true;
};

export const stopAgronomicSpeech = () => {
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel();
    currentUtterance = null;
  }
};

export const isSpeaking = () => {
  if (typeof window === 'undefined' || !window.speechSynthesis) return false;
  return window.speechSynthesis.speaking;
};
