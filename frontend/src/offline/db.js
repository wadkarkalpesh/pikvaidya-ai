/**
 * PikVaidya AI — Client-Side Offline IndexedDB Storage Engine
 * ==========================================================
 * Native W3C IndexedDB implementation providing persistent, zero-dependency
 * local storage for offline crop diagnosis queues, historical diagnostic records,
 * pre-cached agricultural knowledge chunks, and microclimate telemetry.
 * 
 * Stores:
 *   1. offline_queue   - Diagnostic scans captured during network disconnection.
 *   2. cached_history  - Persisted past diagnoses, Grad-CAM overlays, and advisories.
 *   3. cached_knowledge- Offline ICAR/CIBRC pathology and spray recommendations.
 *   4. cached_weather  - Last known microclimate telemetry and 7-day forecast.
 */

const DB_NAME = 'pikvaidya_offline_db';
const DB_VERSION = 1;

/**
 * Initializes and upgrades the IndexedDB database.
 * @returns {Promise<IDBDatabase>}
 */
export function openDB() {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) {
      reject(new Error('IndexedDB is not supported in this browser.'));
      return;
    }

    const request = window.indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // 1. Queue for offline captures
      if (!db.objectStoreNames.contains('offline_queue')) {
        const queueStore = db.createObjectStore('offline_queue', { keyPath: 'id', autoIncrement: true });
        queueStore.createIndex('status', 'status', { unique: false });
        queueStore.createIndex('captured_at', 'captured_at', { unique: false });
      }

      // 2. Cache for historical diagnoses
      if (!db.objectStoreNames.contains('cached_history')) {
        const historyStore = db.createObjectStore('cached_history', { keyPath: 'id' });
        historyStore.createIndex('crop', 'crop', { unique: false });
        historyStore.createIndex('created_at', 'created_at', { unique: false });
      }

      // 3. Cache for agricultural knowledge chunks
      if (!db.objectStoreNames.contains('cached_knowledge')) {
        const knowledgeStore = db.createObjectStore('cached_knowledge', { keyPath: 'chunk_id' });
        knowledgeStore.createIndex('crop', 'crop', { unique: false });
        knowledgeStore.createIndex('language', 'language', { unique: false });
      }

      // 4. Cache for weather telemetry
      if (!db.objectStoreNames.contains('cached_weather')) {
        db.createObjectStore('cached_weather', { keyPath: 'location_key' });
      }
    };

    request.onsuccess = (event) => resolve(event.target.result);
    request.onerror = (event) => reject(event.target.error);
  });
}

/**
 * Adds an un-synced diagnostic capture to the offline queue.
 * @param {Object} item
 * @returns {Promise<number>} Inserted record ID
 */
export async function queueOfflineDiagnosis(item) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('offline_queue', 'readwrite');
    const store = tx.objectStore('offline_queue');

    const record = {
      image_data: item.image_data, // Data URL or Base64 string
      image_name: item.image_name || 'offline_capture.jpg',
      crop: item.crop || 'auto',
      district: item.district || 'Pune',
      latitude: item.latitude || null,
      longitude: item.longitude || null,
      captured_at: item.captured_at || new Date().toISOString(),
      status: 'pending', // 'pending' | 'syncing' | 'synced' | 'failed'
      retry_count: 0,
      error_message: null,
      client_preview: item.client_preview || null
    };

    const req = store.add(record);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Retrieves all pending offline scans awaiting synchronization.
 * @returns {Promise<Array>}
 */
export async function getPendingDiagnoses() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('offline_queue', 'readonly');
    const store = tx.objectStore('offline_queue');
    const req = store.getAll();

    req.onsuccess = () => {
      const pending = (req.result || []).filter(item => item.status === 'pending' || item.status === 'failed');
      resolve(pending);
    };
    req.onerror = () => reject(req.error);
  });
}

/**
 * Updates status and sync outcome of a queued diagnosis.
 * @param {number} id
 * @param {string} status
 * @param {string|null} errorMessage
 * @param {Object|null} syncResult
 */
export async function updateOfflineDiagnosisStatus(id, status, errorMessage = null, syncResult = null) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('offline_queue', 'readwrite');
    const store = tx.objectStore('offline_queue');
    const getReq = store.get(id);

    getReq.onsuccess = () => {
      const record = getReq.result;
      if (!record) {
        resolve(null);
        return;
      }

      record.status = status;
      if (errorMessage) record.error_message = errorMessage;
      if (syncResult) record.sync_result = syncResult;
      if (status === 'syncing') record.retry_count = (record.retry_count || 0) + 1;

      const putReq = store.put(record);
      putReq.onsuccess = () => resolve(record);
      putReq.onerror = () => reject(putReq.error);
    };

    getReq.onerror = () => reject(getReq.error);
  });
}

/**
 * Removes a successfully synchronized diagnosis from queue.
 * @param {number} id
 */
export async function removeOfflineDiagnosis(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('offline_queue', 'readwrite');
    const store = tx.objectStore('offline_queue');
    const req = store.delete(id);
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Caches a successful diagnosis into local history.
 * @param {Object} diagnosis
 */
export async function saveDiagnosisToHistory(diagnosis) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('cached_history', 'readwrite');
    const store = tx.objectStore('cached_history');
    const key = diagnosis.id ? String(diagnosis.id) : `diag_${Date.now()}`;
    const record = { ...diagnosis, id: key, saved_at: new Date().toISOString() };
    const req = store.put(record);
    req.onsuccess = () => resolve(record);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Loads recent diagnosis history from local IndexedDB cache.
 * @param {number} limit
 * @returns {Promise<Array>}
 */
export async function getHistoricalDiagnoses(limit = 20) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('cached_history', 'readonly');
    const store = tx.objectStore('cached_history');
    const req = store.getAll();

    req.onsuccess = () => {
      const results = (req.result || [])
        .sort((a, b) => new Date(b.created_at || b.saved_at) - new Date(a.created_at || a.saved_at))
        .slice(0, limit);
      resolve(results);
    };
    req.onerror = () => reject(req.error);
  });
}

/**
 * Pre-caches agricultural knowledge chunks for offline consultation.
 * @param {Array} chunks
 */
export async function cacheKnowledgeChunks(chunks) {
  if (!chunks || !Array.isArray(chunks)) return;
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('cached_knowledge', 'readwrite');
    const store = tx.objectStore('cached_knowledge');
    chunks.forEach(c => {
      if (c && c.chunk_id) {
        store.put(c);
      }
    });
    tx.oncomplete = () => resolve(chunks.length);
    tx.onerror = () => reject(tx.error);
  });
}

/**
 * Searches offline cached knowledge chunks using client-side lexical scoring.
 * @param {string} crop
 * @param {string} query
 * @param {string} language
 * @returns {Promise<Array>}
 */
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

      // Compute simple client-side keyword relevance score
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

/**
 * Caches microclimate weather telemetry for a district or GPS coordinate.
 * @param {string} locationKey
 * @param {Object} weatherData
 */
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

/**
 * Retrieves cached microclimate weather data.
 * @param {string} locationKey
 * @returns {Promise<Object|null>}
 */
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

/**
 * Returns queue metrics (pending count, failed count).
 * @returns {Promise<{pendingCount: number, failedCount: number, totalQueued: number}>}
 */
export async function getQueueStats() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('offline_queue', 'readonly');
    const store = tx.objectStore('offline_queue');
    const req = store.getAll();

    req.onsuccess = () => {
      const all = req.result || [];
      const pending = all.filter(item => item.status === 'pending');
      const failed = all.filter(item => item.status === 'failed');
      resolve({
        pendingCount: pending.length,
        failedCount: failed.length,
        totalQueued: all.length
      });
    };
    req.onerror = () => reject(req.error);
  });
}
