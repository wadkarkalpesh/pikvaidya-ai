import React, { useState, useEffect } from 'react';
import { X, Search, BookOpen, ExternalLink } from 'lucide-react';
import { searchOfflineKnowledge } from '../offline/db';

export default function OfflineGuideModal({
  isOpen,
  onClose,
  lang,
  t,
  currentCrop
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCrop, setFilterCrop] = useState(currentCrop !== 'auto' ? currentCrop : 'all');
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    async function loadData() {
      setLoading(true);
      try {
        const cropFilter = filterCrop === 'all' ? null : filterCrop;
        const res = await searchOfflineKnowledge(cropFilter, searchTerm, lang);
        setChunks(res || []);
      } catch (err) {
        console.warn('Error querying offline guide:', err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [isOpen, searchTerm, filterCrop, lang]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" style={{ maxWidth: '640px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BookOpen size={20} color="var(--accent-green)" />
            <h3>{t.offlineGuideTitle}</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Search Bar & Crop Filter */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '10px' }} />
              <input
                type="text"
                placeholder={t.searchOfflinePlaceholder || "Search disease symptoms, dosages..."}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem 0.5rem 2.25rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-medium)',
                  fontSize: '0.85rem'
                }}
              />
            </div>

            <select
              value={filterCrop}
              onChange={(e) => setFilterCrop(e.target.value)}
              style={{
                padding: '0.5rem',
                borderRadius: '8px',
                border: '1px solid var(--border-medium)',
                background: '#fff',
                fontSize: '0.85rem'
              }}
            >
              <option value="all">All Crops</option>
              <option value="sugarcane">Sugarcane</option>
              <option value="tomato">Tomato</option>
              <option value="onion">Onion</option>
            </select>
          </div>

          {/* Results List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', maxHeight: '55vh', overflowY: 'auto' }}>
            {chunks.map((item, idx) => (
              <div
                key={idx}
                style={{
                  background: 'var(--bg-secondary)',
                  padding: '0.85rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.35rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {item.disease_name || item.crop}
                  </h4>
                  <span style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem', borderRadius: '4px', background: 'var(--bg-card)', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                    {item.crop} · {item.section || 'General'}
                  </span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {item.text}
                </p>
                {item.source && (
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-light)' }}>
                    📚 Source: {item.source}
                  </span>
                )}
              </div>
            ))}

            {chunks.length === 0 && !loading && (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                {lang === 'mr' ? 'कोणतीही माहिती सापडली नाही.' : 'No offline knowledge matches found.'}
              </div>
            )}

            {loading && (
              <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Searching offline index...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

