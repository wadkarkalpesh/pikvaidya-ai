/**
 * PikVaidya AI — Client-Side Edge AI Inference Engine (ONNX Runtime Web)
 * ====================================================================
 * Enables zero-connectivity, on-device neural pathology classification
 * directly inside the browser using WebAssembly (WASM) and quantized INT8 models.
 * 
 * Pipeline:
 *   1. Canvas-based decode, 224x224 resize, RGB conversion
 *   2. Planar NCHW Float32 tensor construction with ImageNet mean/std normalization
 *   3. Lazy model acquisition with CacheStorage caching
 *   4. WASM execution provider inference
 *   5. Numerically stable softmax probability calibration
 *   6. Top-K classification ranking with offline advisory lookup
 */

import * as ort from 'onnxruntime-web';
import { getAdvisoryCards, searchOfflineKnowledge } from './db.js';

// Configure ONNX Runtime Web WASM binaries
if (typeof window !== 'undefined') {
  ort.env.wasm.wasmPaths = '/';
  ort.env.wasm.numThreads = Math.min(4, typeof navigator !== 'undefined' ? (navigator.hardwareConcurrency || 2) : 2);
}

// Model registry & class mappings
const MODEL_CONFIG = {
  sugarcane: {
    modelUrl: '/models/sugarcane/mobilenet_v3/model_int8.onnx',
    classes: ['Healthy', 'Mosaic', 'RedRot', 'Rust', 'Yellow'],
    name: 'MobileNetV3 INT8 Sugarcane'
  },
  tomato: {
    modelUrl: '/models/tomato/mobilenet_v3/model_int8.onnx',
    classes: [
      'Bacterial_spot',
      'Early_blight',
      'Healthy',
      'Late_blight',
      'Leaf_Mold',
      'Mosaic_virus',
      'Septoria_leaf_spot',
      'Spider_mites',
      'Target_Spot',
      'Yellow_Leaf_Curl_Virus'
    ],
    name: 'MobileNetV3 INT8 Tomato'
  },
  onion: {
    modelUrl: '/models/onion/mobilenet_v3/model_int8.onnx',
    classes: [
      'Onion___healthy',
      'Onion___iris_yellow_virus',
      'Onion___purple_blotch',
      'Onion___stemphylium_blight'
    ],
    name: 'MobileNetV3 INT8 Onion'
  }
};

const CACHE_NAME = 'pikvaidya-onnx-models-v1';
const sessionCache = new Map();

/**
 * Checks whether an ONNX model is already cached in browser CacheStorage.
 * @param {string} crop
 * @returns {Promise<boolean>}
 */
export async function isModelCached(crop) {
  if (typeof window === 'undefined' || !('caches' in window)) return false;
  const config = MODEL_CONFIG[crop.toLowerCase()];
  if (!config) return false;
  try {
    const cache = await caches.open(CACHE_NAME);
    const match = await cache.match(config.modelUrl);
    return !!match;
  } catch (e) {
    return false;
  }
}

/**
 * Pre-downloads and caches an ONNX model for offline use.
 * @param {string} crop
 * @param {Function} [onProgress]
 * @returns {Promise<boolean>}
 */
export async function cacheModelForOffline(crop, onProgress = null) {
  const config = MODEL_CONFIG[crop.toLowerCase()];
  if (!config) throw new Error(`Unsupported crop type: ${crop}`);

  if (typeof window === 'undefined' || !('caches' in window)) {
    throw new Error('CacheStorage API is not supported in this browser.');
  }

  const cache = await caches.open(CACHE_NAME);
  const existing = await cache.match(config.modelUrl);
  if (existing) {
    if (onProgress) onProgress(100);
    return true;
  }

  const response = await fetch(config.modelUrl);
  if (!response.ok) {
    throw new Error(`Failed to download model for ${crop}: HTTP ${response.status}`);
  }

  // Clone response to put into cache
  await cache.put(config.modelUrl, response.clone());
  if (onProgress) onProgress(100);
  return true;
}

/**
 * Loads an ONNX inference session with WASM execution provider.
 * Uses cached ArrayBuffer if available offline.
 * @param {string} crop
 * @returns {Promise<ort.InferenceSession>}
 */
export async function getInferenceSession(crop) {
  const cropKey = crop.toLowerCase();
  if (sessionCache.has(cropKey)) {
    return sessionCache.get(cropKey);
  }

  const config = MODEL_CONFIG[cropKey];
  if (!config) {
    throw new Error(`Unknown crop: ${crop}. Supported crops: sugarcane, tomato, onion.`);
  }

  let modelBuffer = null;

  // Attempt CacheStorage fetch first
  if (typeof window !== 'undefined' && 'caches' in window) {
    try {
      const cache = await caches.open(CACHE_NAME);
      const cachedResponse = await cache.match(config.modelUrl);
      if (cachedResponse) {
        modelBuffer = await cachedResponse.arrayBuffer();
        console.log(`[PikVaidya Edge] Loaded ${crop} model from browser CacheStorage.`);
      }
    } catch (err) {
      console.warn('[PikVaidya Edge] CacheStorage read failed, falling back to network fetch:', err);
    }
  }

  // Network fetch if not in CacheStorage
  if (!modelBuffer) {
    const res = await fetch(config.modelUrl);
    if (!res.ok) {
      throw new Error(`Model file not accessible: ${config.modelUrl} (HTTP ${res.status}). Ensure the model is cached while online.`);
    }
    const clone = res.clone();
    modelBuffer = await res.arrayBuffer();

    // Cache for future offline use
    if (typeof window !== 'undefined' && 'caches' in window) {
      try {
        const cache = await caches.open(CACHE_NAME);
        await cache.put(config.modelUrl, clone);
      } catch (e) {
        console.warn('[PikVaidya Edge] Failed to cache model response:', e);
      }
    }
  }

  // Create ONNX Inference Session with WASM
  const session = await ort.InferenceSession.create(modelBuffer, {
    executionProviders: ['wasm'],
    graphOptimizationLevel: 'all'
  });

  sessionCache.set(cropKey, session);
  return session;
}

/**
 * Preprocesses an image element, canvas, or data URL into a planar NCHW [1, 3, 224, 224] Float32Array tensor.
 * Standard ImageNet normalization:
 *   mean = [0.485, 0.456, 0.406]
 *   std  = [0.229, 0.224, 0.225]
 * @param {HTMLImageElement|HTMLCanvasElement|ImageBitmap|string} imageSource
 * @returns {Promise<ort.Tensor>}
 */
export async function preprocessImage(imageSource) {
  let imgElement;

  if (typeof imageSource === 'string') {
    imgElement = await new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => resolve(img);
      img.onerror = (e) => reject(new Error('Failed to load image source for edge preprocessing.'));
      img.src = imageSource;
    });
  } else if (imageSource instanceof HTMLImageElement || imageSource instanceof ImageBitmap) {
    imgElement = imageSource;
  } else if (imageSource instanceof HTMLCanvasElement) {
    imgElement = imageSource;
  } else {
    throw new Error('Unsupported image source type for edge preprocessing.');
  }

  // Create offscreen canvas for 224x224 bilinear scaling
  const canvas = document.createElement('canvas');
  canvas.width = 224;
  canvas.height = 224;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  ctx.drawImage(imgElement, 0, 0, 224, 224);
  const imageData = ctx.getImageData(0, 0, 224, 224);
  const rgba = imageData.data;

  const float32Data = new Float32Array(1 * 3 * 224 * 224);
  const channelStride = 224 * 224;

  const mean = [0.485, 0.456, 0.406];
  const std = [0.229, 0.224, 0.225];

  for (let i = 0; i < channelStride; i++) {
    const r = rgba[i * 4 + 0] / 255.0;
    const g = rgba[i * 4 + 1] / 255.0;
    const b = rgba[i * 4 + 2] / 255.0;

    float32Data[0 * channelStride + i] = (r - mean[0]) / std[0];
    float32Data[1 * channelStride + i] = (g - mean[1]) / std[1];
    float32Data[2 * channelStride + i] = (b - mean[2]) / std[2];
  }

  return new ort.Tensor('float32', float32Data, [1, 3, 224, 224]);
}

/**
 * Computes numerically stable softmax over raw logits.
 * @param {Float32Array|Array<number>} logits
 * @returns {Array<number>}
 */
export function softmax(logits) {
  let maxLogit = -Infinity;
  for (let i = 0; i < logits.length; i++) {
    if (logits[i] > maxLogit) maxLogit = logits[i];
  }

  let sumExp = 0.0;
  const expLogits = new Array(logits.length);
  for (let i = 0; i < logits.length; i++) {
    const e = Math.exp(logits[i] - maxLogit);
    expLogits[i] = e;
    sumExp += e;
  }

  return expLogits.map(v => v / (sumExp || 1.0));
}

/**
 * Executes edge AI neural inference on client device.
 * @param {string} crop
 * @param {HTMLImageElement|string} imageSource
 * @returns {Promise<Object>}
 */
export async function runLocalEdgeInference(crop, imageSource) {
  const startTime = performance.now();
  const cropKey = crop.toLowerCase();
  const config = MODEL_CONFIG[cropKey];

  if (!config) {
    throw new Error(`Crop '${crop}' is not supported for on-device inference.`);
  }

  // 1. Load session
  const session = await getInferenceSession(cropKey);

  // 2. Preprocess image
  const inputTensor = await preprocessImage(imageSource);

  // 3. Run inference
  const feeds = { [session.inputNames[0]]: inputTensor };
  const results = await session.run(feeds);
  const outputTensor = results[session.outputNames[0]];

  // 4. Calibrate probabilities
  const logits = outputTensor.data;
  const probabilities = softmax(logits);

  // 5. Map to class labels
  const ranked = config.classes.map((className, idx) => ({
    disease: className,
    probability: probabilities[idx],
    confidence_percentage: Math.round(probabilities[idx] * 1000) / 10
  })).sort((a, b) => b.probability - a.probability);

  const topPrediction = ranked[0];
  const endTime = performance.now();
  const durationMs = Math.round(endTime - startTime);

  // 6. Retrieve offline advisory cards for top prediction
  let localAdvisory = [];
  try {
    const cards = await getAdvisoryCards({ cropType: cropKey, disease: topPrediction.disease });
    if (cards && cards.length > 0) {
      localAdvisory = cards.map(c => c.advisory_text);
    } else {
      const knowledge = await searchOfflineKnowledge(cropKey, topPrediction.disease);
      if (knowledge && knowledge.length > 0) {
        localAdvisory = knowledge.map(k => k.snippet || k.text);
      }
    }
  } catch (e) {
    console.warn('[PikVaidya Edge] Advisory lookup warning:', e);
  }

  // Fallback advisory if no offline card exists
  if (localAdvisory.length === 0) {
    localAdvisory = [
      `Local diagnosis: ${topPrediction.disease}. Ensure adequate aeration and isolate symptomatic foliage.`,
      `Sync with cloud when internet connection is restored for Grad-CAM visual heatmaps and expert ICAR pesticide dosage.`
    ];
  }

  return {
    crop: cropKey,
    predicted_disease: topPrediction.disease,
    confidence: topPrediction.probability,
    confidence_percentage: topPrediction.confidence_percentage,
    top_predictions: ranked,
    inference_time_ms: durationMs,
    is_local_inference: true,
    gradcam_available: false,
    gradcam_url: null,
    gradcam_notice: 'Grad-CAM visual explainability requires cloud connectivity. Queued for background sync.',
    recommendations: localAdvisory,
    risk_level: topPrediction.disease.toLowerCase().includes('healthy') ? 'LOW' : 'HIGH',
    timestamp: new Date().toISOString()
  };
}

