import React, { useState } from 'react';
import { X, Plus, Trash2, Sprout, MapPin } from 'lucide-react';

export default function FarmModal({
  isOpen,
  onClose,
  farms,
  onSaveFarm,
  onDeleteFarm,
  lang,
  district
}) {
  const [name, setName] = useState('');
  const [crop, setCrop] = useState('sugarcane');
  const [variety, setVariety] = useState('');
  const [area, setArea] = useState('2.5');
  const [soilType, setSoilType] = useState('Black Cotton');
  const [irrigation, setIrrigation] = useState('Drip');
  const [sowingDate, setSowingDate] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    onSaveFarm({
      id: Date.now().toString(),
      name: name.trim(),
      crop,
      variety: variety.trim(),
      area: parseFloat(area) || 1.0,
      soil_type: soilType,
      irrigation,
      sowing_date: sowingDate,
      district: district || 'pune'
    });

    setName('');
    setVariety('');
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sprout size={20} color="var(--accent-green)" />
            <h3>{lang === 'mr' ? 'माझी शेती व भूखंड व्यवस्थापन' : 'My Farm Plots & Fields'}</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Add New Plot Form */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', background: 'var(--bg-secondary)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {lang === 'mr' ? 'नवीन भूखंड जोडा (Add New Plot)' : 'Add New Farm Plot'}
            </h4>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.5rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Plot Name / Gat No.</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Gat No. 84 / South Plot"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  style={{ width: '100%', padding: '0.45rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Area (Acres)</label>
                <input
                  type="number"
                  step="0.1"
                  value={area}
                  onChange={(e) => setArea(e.target.value)}
                  style={{ width: '100%', padding: '0.45rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Crop Type</label>
                <select
                  value={crop}
                  onChange={(e) => setCrop(e.target.value)}
                  style={{ width: '100%', padding: '0.45rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem', background: '#fff' }}
                >
                  <option value="sugarcane">Sugarcane (ऊस)</option>
                  <option value="tomato">Tomato (टोमॅटो)</option>
                  <option value="onion">Onion (कांदा)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Crop Variety</label>
                <input
                  type="text"
                  placeholder="e.g. Co 86032 / Bhima Super"
                  value={variety}
                  onChange={(e) => setVariety(e.target.value)}
                  style={{ width: '100%', padding: '0.45rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Irrigation</label>
                <select
                  value={irrigation}
                  onChange={(e) => setIrrigation(e.target.value)}
                  style={{ width: '100%', padding: '0.45rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem', background: '#fff' }}
                >
                  <option value="Drip">Drip Irrigation (ठिबक)</option>
                  <option value="Flood">Flood / Furrow (पाटपाणी)</option>
                  <option value="Sprinkler">Sprinkler (तुषार)</option>
                  <option value="Rainfed">Rainfed (जिरायती)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Soil Type</label>
                <select
                  value={soilType}
                  onChange={(e) => setSoilType(e.target.value)}
                  style={{ width: '100%', padding: '0.45rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem', background: '#fff' }}
                >
                  <option value="Black Cotton">Black Cotton (काळी माती)</option>
                  <option value="Alluvial">Alluvial (गाळाची माती)</option>
                  <option value="Red Loam">Red Loam (तांबडी माती)</option>
                  <option value="Sandy Loam">Sandy Loam (वाळुसर)</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              className="topbar-btn"
              style={{ background: 'var(--accent-terracotta)', color: '#fff', justifyContent: 'center', borderColor: 'transparent', fontWeight: 600, marginTop: '0.25rem' }}
            >
              <Plus size={15} />
              <span>{lang === 'mr' ? 'भूखंड जतन करा' : 'Save Plot Record'}</span>
            </button>
          </form>

          {/* Existing Plots List */}
          <div>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              {lang === 'mr' ? 'नोंदणीकृत भूखंड' : 'Registered Farm Plots'} ({farms.length})
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {farms.map((f) => (
                <div
                  key={f.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.65rem 0.85rem',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                      {f.crop === 'sugarcane' ? '🍬 ' : f.crop === 'tomato' ? '🍅 ' : '🧅 '}
                      {f.name}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {f.area} Acres · {f.variety || f.crop} · {f.irrigation} · {f.soil_type}
                    </div>
                  </div>

                  <button
                    onClick={() => onDeleteFarm(f.id)}
                    style={{ background: 'none', border: 'none', color: 'var(--text-light)', cursor: 'pointer', padding: '0.25rem' }}
                    title="Remove plot"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}

              {farms.length === 0 && (
                <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  No farm plots added yet. Add your first plot above.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

