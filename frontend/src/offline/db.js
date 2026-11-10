/**
 * PikVaidya AI — Client-Side Offline IndexedDB Storage Engine (W3C Standard)
 * =========================================================================
 * Comprehensive IndexedDB implementation providing persistent, offline storage
 * for rural Maharashtra agricultural deployment.
 * 
 * Target Stores:
 *   1. diagnosis_history:
 *      - diagnosis_id (PK)
 *      - crop_type, predicted_disease, confidence
 *      - image_reference (base64 / dataUrl / blobRef)
 *      - gradcam_reference (URL/dataUrl or null if local edge inference)
 *      - latitude, longitude
 *      - diagnosis_timestamp (ISO)
 *      - sync_status ('synced' | 'pending_sync' | 'local_only')
 *      - is_local_inference (boolean)
 *      Indexes: by_crop, by_date, by_sync_status
 * 
 *   2. farm_information:
 *      - farm_id (PK)
 *      - farmer_id, farm_name, latitude, longitude
 *      - crop_type, crop_growth_stage, updated_at
 *      Indexes: by_farmer, by_crop
 * 
 *   3. advisory_cards:
 *      - advisory_id (PK)
 *      - crop_type, disease, advisory_text, language, source, created_at, expires_at
 *      Indexes: by_crop, by_disease, by_language
 * 
 *   4. sync_queue:
 *      - queue_id (PK)
 *      - operation_type, payload, created_at, retry_count, sync_status, last_error, idempotency_key
 *      Indexes: by_status, by_created_at, by_idempotency
 * 
 * Also maintains backward-compatible aliases for cached_knowledge and cached_weather.
 */

export const DB_NAME = 'pikvaidya_offline_db';
export const DB_VERSION = 2;

/**
 * Opens and initializes the IndexedDB database schema with versioning and upgrade hooks.
 * @returns {Promise<IDBDatabase>}
 */
export function openDB() {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      reject(new Error('IndexedDB is not supported in this runtime environment.'));
      return;
    }

    const request = window.indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      const oldVersion = event.oldVersion;

      // 1. diagnosis_history store
      if (!db.objectStoreNames.contains('diagnosis_history')) {
        const store = db.createObjectStore('diagnosis_history', { keyPath: 'diagnosis_id' });
        store.createIndex('by_crop', 'crop_type', { unique: false });
        store.createIndex('by_date', 'diagnosis_timestamp', { unique: false });
        store.createIndex('by_sync_status', 'sync_status', { unique: false });
      }

      // 2. farm_information store
      if (!db.objectStoreNames.contains('farm_information')) {
        const store = db.createObjectStore('farm_information', { keyPath: 'farm_id' });
        store.createIndex('by_farmer', 'farmer_id', { unique: false });
        store.createIndex('by_crop', 'crop_type', { unique: false });
      }

      // 3. advisory_cards store
      if (!db.objectStoreNames.contains('advisory_cards')) {
        const store = db.createObjectStore('advisory_cards', { keyPath: 'advisory_id' });
        store.createIndex('by_crop', 'crop_type', { unique: false });
        store.createIndex('by_disease', 'disease', { unique: false });
        store.createIndex('by_language', 'language', { unique: false });
      }

      // 4. sync_queue store
      if (!db.objectStoreNames.contains('sync_queue')) {
        const store = db.createObjectStore('sync_queue', { keyPath: 'queue_id' });
        store.createIndex('by_status', 'sync_status', { unique: false });
        store.createIndex('by_created_at', 'created_at', { unique: false });
        store.createIndex('by_idempotency', 'idempotency_key', { unique: false });
      }

      // Backward-compatible auxiliary stores
      if (!db.objectStoreNames.contains('offline_queue')) {
        const qStore = db.createObjectStore('offline_queue', { keyPath: 'id', autoIncrement: true });
        qStore.createIndex('status', 'status', { unique: false });
        qStore.createIndex('captured_at', 'captured_at', { unique: false });
      }

      if (!db.objectStoreNames.contains('cached_history')) {
        const hStore = db.createObjectStore('cached_history', { keyPath: 'id' });
        hStore.createIndex('crop', 'crop', { unique: false });
        hStore.createIndex('created_at', 'created_at', { unique: false });
      }

      if (!db.objectStoreNames.contains('cached_knowledge')) {
        const kStore = db.createObjectStore('cached_knowledge', { keyPath: 'chunk_id' });
        kStore.createIndex('crop', 'crop', { unique: false });
        kStore.createIndex('language', 'language', { unique: false });
      }

      if (!db.objectStoreNames.contains('cached_weather')) {
        db.createObjectStore('cached_weather', { keyPath: 'location_key' });
      }
    };

    request.onsuccess = (event) => resolve(event.target.result);
    request.onerror = (event) => reject(event.target.error);
    request.onblocked = () => {
      console.warn('[PikVaidya IDB] Upgrade blocked by open connection in another tab.');
    };
  });
}

// ==========================================
// STORE 1: diagnosis_history CRUD Operations
// ==========================================

/**
 * Saves or updates a diagnosis record in diagnosis_history.
 * @param {Object} diag
 * @returns {Promise<Object>}
 */
export async function saveDiagnosis(diag) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    try {
      const tx = db.transaction('diagnosis_history', 'readwrite');
      const store = tx.objectStore('diagnosis_history');

      const diagnosisId = diag.diagnosis_id || diag.id || `diag_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      const record = {
        diagnosis_id: String(diagnosisId),
        crop_type: (diag.crop_type || diag.crop_name || diag.crop || 'unknown').toLowerCase(),
        predicted_disease: diag.predicted_disease || diag.disease || 'Unknown Condition',
        confidence: typeof diag.confidence === 'number' ? diag.confidence : 0.0,
        image_reference: diag.image_reference || diag.image_data || diag.client_preview || null,
        gradcam_reference: diag.gradcam_reference || diag.gradcam_url || diag.gradcam_image || null,
        latitude: diag.latitude !== undefined ? Number(diag.latitude) : null,
        longitude: diag.longitude !== undefined ? Number(diag.longitude) : null,
        diagnosis_timestamp: diag.diagnosis_timestamp || diag.created_at || diag.captured_at || new Date().toISOString(),
        sync_status: diag.sync_status || (diag.is_local_inference ? 'local_only' : 'synced'),
        is_local_inference: Boolean(diag.is_local_inference),
        recommendations: diag.recommendations || diag.advisory || [],
        weather_risk_assessment: diag.weather_risk_assessment || null,
        risk_level: diag.risk_level || 'LOW'
      };

      const req = store.put(record);
      req.onsuccess = () => resolve(record);
      req.onerror = (e) => {
        if (e.target.error && e.target.error.name === 'QuotaExceededError') {
          console.error('[PikVaidya IDB] Storage quota exceeded while saving diagnosis.');
        }
        reject(e.target.error);
      };
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Retrieves a single diagnosis record by diagnosis_id.
 * @param {string} diagnosisId
 * @returns {Promise<Object|null>}
 */
export async function getDiagnosisById(diagnosisId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('diagnosis_history', 'readonly');
    const store = tx.objectStore('diagnosis_history');
    const req = store.get(String(diagnosisId));
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Queries diagnoses with optional crop filter, sync_status filter, and pagination.
 * @param {Object} options
 * @returns {Promise<Array>}
 */
export async function getAllDiagnoses({ cropType = null, syncStatus = null, limit = 50 } = {}) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('diagnosis_history', 'readonly');
    const store = tx.objectStore('diagnosis_history');
    const req = store.getAll();

    req.onsuccess = () => {
      let results = req.result || [];
      if (cropType && cropType !== 'all') {
        results = results.filter(d => (d.crop_type || '').toLowerCase() === cropType.toLowerCase());
      }
      if (syncStatus) {
        results = results.filter(d => d.sync_status === syncStatus);
      }
      // Sort newest first
      results.sort((a, b) => new Date(b.diagnosis_timestamp) - new Date(a.diagnosis_timestamp));
      resolve(results.slice(0, limit));
    };
    req.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Deletes a diagnosis record by diagnosis_id.
 * @param {string} diagnosisId
 * @returns {Promise<boolean>}
 */
export async function deleteDiagnosis(diagnosisId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('diagnosis_history', 'readwrite');
    const store = tx.objectStore('diagnosis_history');
    const req = store.delete(String(diagnosisId));
    req.onsuccess = () => resolve(true);
    req.onerror = (e) => reject(e.target.error);
  });
}

// ==========================================
// STORE 2: farm_information CRUD Operations
// ==========================================

/**
 * Saves farm profile and geolocation data.
 * @param {Object} farm
 * @returns {Promise<Object>}
 */
export async function saveFarmInfo(farm) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('farm_information', 'readwrite');
    const store = tx.objectStore('farm_information');

    const farmId = farm.farm_id || `farm_${Date.now()}`;
    const record = {
      farm_id: String(farmId),
      farmer_id: String(farm.farmer_id || 'farmer_default'),
      farm_name: farm.farm_name || 'My Farm',
      latitude: farm.latitude ? Number(farm.latitude) : 18.5204, // Default Maharashtra (Pune)
      longitude: farm.longitude ? Number(farm.longitude) : 73.8567,
      crop_type: (farm.crop_type || 'sugarcane').toLowerCase(),
      crop_growth_stage: farm.crop_growth_stage || 'Vegetative',
      updated_at: new Date().toISOString()
    };

    const req = store.put(record);
    req.onsuccess = () => resolve(record);
    req.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Retrieves all registered farms.
 * @returns {Promise<Array>}
 */
export async function getAllFarms() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('farm_information', 'readonly');
    const store = tx.objectStore('farm_information');
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = (e) => reject(e.target.error);
  });
}

// ==========================================
// STORE 3: advisory_cards CRUD Operations
// ==========================================

/**
 * Persists an agricultural advisory card into offline storage.
 * @param {Object} card
 * @returns {Promise<Object>}
 */
export async function saveAdvisoryCard(card) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('advisory_cards', 'readwrite');
    const store = tx.objectStore('advisory_cards');

    const advisoryId = card.advisory_id || `adv_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const record = {
      advisory_id: String(advisoryId),
      crop_type: (card.crop_type || 'all').toLowerCase(),
      disease: card.disease || 'General Care',
      advisory_text: card.advisory_text || card.recommendation || '',
      language: card.language || 'en',
      source: card.source || 'ICAR / VNMKV / MPKV',
      created_at: card.created_at || new Date().toISOString(),
      expires_at: card.expires_at || new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString()
    };

    const req = store.put(record);
    req.onsuccess = () => resolve(record);
    req.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Retrieves cached advisory cards matching crop, disease and language.
 * @param {Object} filter
 * @returns {Promise<Array>}
 */
export async function getAdvisoryCards({ cropType = null, disease = null, language = null } = {}) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('advisory_cards', 'readonly');
    const store = tx.objectStore('advisory_cards');
    const req = store.getAll();

    req.onsuccess = () => {
      let cards = req.result || [];
      if (cropType && cropType !== 'all') {
        cards = cards.filter(c => c.crop_type === 'all' || c.crop_type.toLowerCase() === cropType.toLowerCase());
      }
      if (disease && disease !== 'all') {
        cards = cards.filter(c => c.disease.toLowerCase().includes(disease.toLowerCase()));
      }
      if (language) {
        cards = cards.filter(c => c.language === language);
      }
      resolve(cards);
    };
    req.onerror = (e) => reject(e.target.error);
  });
}

// ==========================================
// STORE 4: sync_queue Operations
// ==========================================

/**
 * Enqueues a sync operation into sync_queue with idempotency key.
 * @param {Object} op
 * @returns {Promise<Object>}
 */
export async function enqueueSyncOperation(op) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_queue', 'readwrite');
    const store = tx.objectStore('sync_queue');

    const queueId = op.queue_id || `q_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const idempotencyKey = op.idempotency_key || `idem_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    const record = {
      queue_id: String(queueId),
      operation_type: op.operation_type || 'DIAGNOSIS_UPLOAD',
      payload: op.payload || {},
      created_at: op.created_at || new Date().toISOString(),
      retry_count: typeof op.retry_count === 'number' ? op.retry_count : 0,
      sync_status: 'pending', // 'pending' | 'syncing' | 'failed'
      last_error: null,
      idempotency_key: idempotencyKey
    };

    const req = store.put(record);
    req.onsuccess = () => resolve(record);
    req.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Retrieves all pending items in sync_queue.
 * @returns {Promise<Array>}
 */
export async function getPendingSyncQueue() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_queue', 'readonly');
    const store = tx.objectStore('sync_queue');
    const req = store.getAll();

    req.onsuccess = () => {
      const all = req.result || [];
      const pending = all.filter(item => item.sync_status === 'pending' || item.sync_status === 'failed');
      pending.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
      resolve(pending);
    };
    req.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Updates status, retry count and error details for a queued sync item.
 * @param {string} queueId
 * @param {string} status
 * @param {string|null} lastError
 * @returns {Promise<Object|null>}
 */
export async function updateSyncQueueStatus(queueId, status, lastError = null) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_queue', 'readwrite');
    const store = tx.objectStore('sync_queue');
    const getReq = store.get(String(queueId));

    getReq.onsuccess = () => {
      const record = getReq.result;
      if (!record) {
        resolve(null);
        return;
      }
      record.sync_status = status;
      if (lastError !== null) record.last_error = String(lastError);
      if (status === 'syncing') record.retry_count = (record.retry_count || 0) + 1;

      const putReq = store.put(record);
      putReq.onsuccess = () => resolve(record);
      putReq.onerror = (e) => reject(e.target.error);
    };
    getReq.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Deletes a completed sync operation from sync_queue.
 * @param {string} queueId
 * @returns {Promise<boolean>}
 */
export async function removeSyncQueueItem(queueId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_queue', 'readwrite');
    const store = tx.objectStore('sync_queue');
    const req = store.delete(String(queueId));
    req.onsuccess = () => resolve(true);
    req.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Returns quantitative metrics of the sync queue.
 * @returns {Promise<{pendingCount: number, failedCount: number, totalQueued: number}>}
 */
export async function getSyncQueueStats() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_queue', 'readonly');
    const store = tx.objectStore('sync_queue');
    const req = store.getAll();

    req.onsuccess = () => {
      const all = req.result || [];
      const pending = all.filter(i => i.sync_status === 'pending');
      const failed = all.filter(i => i.sync_status === 'failed');
      resolve({
        pendingCount: pending.length,
        failedCount: failed.length,
        totalQueued: all.length
      });
    };
    req.onerror = (e) => reject(e.target.error);
  });
}

// ==========================================
// STORAGE MANAGEMENT & DIAGNOSTIC EXPORT
// ==========================================

/**
 * Queries current browser storage usage and quota.
 * @returns {Promise<{usage: number, quota: number, percentUsed: number, usageMB: number, quotaMB: number}>}
 */
export async function getStorageEstimate() {
  if (typeof navigator !== 'undefined' && navigator.storage && navigator.storage.estimate) {
    try {
      const estimate = await navigator.storage.estimate();
      const usage = estimate.usage || 0;
      const quota = estimate.quota || 1;
      return {
        usage,
        quota,
        percentUsed: Math.round((usage / quota) * 100),
        usageMB: (usage / (1024 * 1024)).toFixed(2),
        quotaMB: (quota / (1024 * 1024)).toFixed(2)
      };
    } catch (e) {
      console.warn('[PikVaidya Storage] Could not estimate quota:', e);
    }
  }
  return { usage: 0, quota: 0, percentUsed: 0, usageMB: '0.00', quotaMB: '0.00' };
}

/**
 * Exports entire IndexedDB state across all stores to structured JSON for backup.
 * @returns {Promise<string>}
 */
export async function exportDatabaseToJson() {
  const db = await openDB();
  const stores = ['diagnosis_history', 'farm_information', 'advisory_cards', 'sync_queue', 'cached_knowledge', 'cached_weather'];
  const dump = {
    exported_at: new Date().toISOString(),
    version: DB_VERSION,
    stores: {}
  };

  for (const storeName of stores) {
    if (db.objectStoreNames.contains(storeName)) {
      dump.stores[storeName] = await new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, 'readonly');
        const req = tx.objectStore(storeName).getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = (e) => reject(e.target.error);
      });
    }
  }

  return JSON.stringify(dump, null, 2);
}

// ========================================================
// BACKWARD-COMPATIBILITY ALIASES (Prevents Phase 7 Breakage)
// ========================================================

export async function queueOfflineDiagnosis(item) {
  const queueItem = await enqueueSyncOperation({
    operation_type: 'DIAGNOSIS_UPLOAD',
    payload: item,
    created_at: item.captured_at
  });

  // Mirror in diagnosis_history as pending_sync
  await saveDiagnosis({
    diagnosis_id: queueItem.queue_id,
    crop_type: item.crop,
    predicted_disease: item.client_preview ? item.client_preview.predicted_disease : 'Pending Cloud Sync',
    confidence: item.client_preview ? item.client_preview.confidence : 0.0,
    image_reference: item.image_data,
    latitude: item.latitude,
    longitude: item.longitude,
    diagnosis_timestamp: item.captured_at || new Date().toISOString(),
    sync_status: 'pending_sync',
    is_local_inference: Boolean(item.is_local_inference)
  });

  return queueItem.queue_id;
}

export async function getPendingDiagnoses() {
  return getPendingSyncQueue();
}

export async function updateOfflineDiagnosisStatus(id, status, errorMessage = null, syncResult = null) {
  return updateSyncQueueStatus(id, status, errorMessage);
}

export async function removeOfflineDiagnosis(id) {
  return removeSyncQueueItem(id);
}

export async function saveDiagnosisToHistory(diagnosis) {
  return saveDiagnosis(diagnosis);
}

export async function getHistoricalDiagnoses(limit = 20) {
  return getAllDiagnoses({ limit });
}

export async function cacheKnowledgeChunks(chunks) {
  if (!chunks || !Array.isArray(chunks)) return;
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('cached_knowledge', 'readwrite');
    const store = tx.objectStore('cached_knowledge');
    chunks.forEach(c => {
      if (c && c.chunk_id) store.put(c);
    });
    tx.oncomplete = () => resolve(chunks.length);
    tx.onerror = () => reject(tx.error);
  });
}

export async function searchOfflineKnowledge(crop = null, query = '', language = 'en') {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('cached_knowledge', 'readonly');
    const store = tx.objectStore('cached_knowledge');
    const req = store.getAll();

    req.onsuccess = () => {
      const allChunks = req.result || [];
      const qTokens = (query || '').toLowerCase().split(/\s+/).filter(w => w.length > 2);

      const filtered = allChunks.filter(c => {
        if (crop && c.crop && c.crop.toLowerCase() !== crop.toLowerCase()) return false;
        if (language && c.language && c.language.toLowerCase() !== language.toLowerCase()) return false;
        return true;
      });

      if (qTokens.length === 0) {
        resolve(filtered.slice(0, 10));
        return;
      }

      const scored = filtered.map(c => {
        let score = 0;
        const textLower = (c.text || c.snippet || '').toLowerCase();
        qTokens.forEach(t => {
          if (textLower.includes(t)) score += 1;
        });
        return { chunk: c, score };
      }).filter(item => item.score > 0);

      scored.sort((a, b) => b.score - a.score);
      resolve(scored.slice(0, 10).map(s => s.chunk));
    };

    req.onerror = () => reject(req.error);
  });
}

export async function cacheWeather(locationKey, weatherData) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('cached_weather', 'readwrite');
    const store = tx.objectStore('cached_weather');
    const record = {
      location_key: locationKey,
      data: weatherData,
      cached_at: new Date().toISOString()
    };
    const req = store.put(record);
    req.onsuccess = () => resolve(record);
    req.onerror = () => reject(req.error);
  });
}

export async function getCachedWeather(locationKey) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('cached_weather', 'readonly');
    const store = tx.objectStore('cached_weather');
    const req = store.get(locationKey);
    req.onsuccess = () => resolve(req.result ? req.result.data : null);
    req.onerror = () => reject(req.error);
  });
}

export async function getQueueStats() {
  return getSyncQueueStats();
}
