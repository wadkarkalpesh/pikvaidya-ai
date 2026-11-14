import React, { useState, useEffect } from 'react';
import { X, User, Shield, CheckCircle, Bell, MapPin, Globe } from 'lucide-react';

export default function ProfileModal({
  isOpen,
  onClose,
  profile,
  onSaveProfile,
  lang,
  onLangChange,
  districtsList
}) {
  const [name, setName] = useState(profile?.name || 'Ramesh Patil');
  const [mobile, setMobile] = useState(profile?.mobile || '9822012345');
  const [district, setDistrict] = useState(profile?.district || 'pune');
  const [locationConsent, setLocationConsent] = useState(profile?.locationConsent ?? true);
  const [notifyConsent, setNotifyConsent] = useState(profile?.notifyConsent ?? true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (profile) {
      setName(profile.name || 'Ramesh Patil');
      setMobile(profile.mobile || '9822012345');
      setDistrict(profile.district || 'pune');
      setLocationConsent(profile.locationConsent ?? true);
      setNotifyConsent(profile.notifyConsent ?? true);
    }
  }, [profile, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSaveProfile({
      name: name.trim(),
      mobile: mobile.trim(),
      district,
      locationConsent,
      notifyConsent
    });
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 1200);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" style={{ maxWidth: '480px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <User size={20} color="var(--accent-terracotta)" />
            <h3>{lang === 'mr' ? 'शेतकरी प्रोफाईल व संमती' : 'Farmer Profile & Consent Settings'}</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {savedSuccess ? (
            <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--accent-green)' }}>
              <CheckCircle size={40} style={{ margin: '0 auto 0.5rem auto' }} />
              <h4>{lang === 'mr' ? 'माहिती जतन केली!' : 'Profile Saved Successfully!'}</h4>
            </div>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {lang === 'mr' ? 'शेतकऱ्याचे नाव' : 'Farmer Full Name'}
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {lang === 'mr' ? 'मोबाईल नंबर' : 'Mobile Number'}
                </label>
                <input
                  type="tel"
                  required
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {lang === 'mr' ? 'प्राथमिक जिल्हा' : 'Primary Agricultural District'}
                </label>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem', background: '#fff' }}
                >
                  {districtsList.map((d) => (
                    <option key={d.id} value={d.id}>
                      {lang === 'mr' ? d.name_mr : d.name} (Maharashtra)
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
              </div>

              {/* Language Selection */}
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {lang === 'mr' ? 'प्राधान्य दिलेली भाषा' : 'Preferred Language'}
                </label>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                  <button
                    type="button"
                    className={`lang-tab ${lang === 'mr' ? 'active' : ''}`}
                    onClick={() => onLangChange('mr')}
                    style={{ flex: 1, padding: '0.45rem', border: '1px solid var(--border-subtle)' }}
                  >
                    मराठी
                  </button>
                  <button
                    type="button"
                    className={`lang-tab ${lang === 'hi' ? 'active' : ''}`}
                    onClick={() => onLangChange('hi')}
                    style={{ flex: 1, padding: '0.45rem', border: '1px solid var(--border-subtle)' }}
                  >
                    हिंदी
                  </button>
                  <button
                    type="button"
                    className={`lang-tab ${lang === 'en' ? 'active' : ''}`}
                    onClick={() => onLangChange('en')}
                    style={{ flex: 1, padding: '0.45rem', border: '1px solid var(--border-subtle)' }}
                  >
                    English
                  </button>
                </div>
              </div>

              {/* Consent Checkboxes (SRS FR-007) */}
              <div style={{ background: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  🛡️ {lang === 'mr' ? 'कायदेशीर संमती व गोपनीयता' : 'Statutory Consent & Privacy (FR-007)'}
                </span>

                <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={locationConsent}
                    onChange={(e) => setLocationConsent(e.target.checked)}
                    style={{ marginTop: '2px', accentColor: 'var(--accent-terracotta)' }}
                  />
                  <span>
                    {lang === 'mr'
                      ? 'हवामान व फवारणी धोके मोजण्यासाठी GPS स्थानाचा वापर करण्यास माझी संमती आहे.'
                      : 'I consent to use GPS farm coordinates strictly for microclimate telemetry and disease conduciveness analysis.'}
                  </span>
                </label>

                <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={notifyConsent}
                    onChange={(e) => setNotifyConsent(e.target.checked)}
                    style={{ marginTop: '2px', accentColor: 'var(--accent-terracotta)' }}
                  />
                  <span>
                    {lang === 'mr'
                      ? 'स्थानिक कीड व रोग प्रादुर्भावाच्या हवामान सूचना प्राप्त करण्यास माझी अनुमती आहे.'
                      : 'I consent to receive pest risk alerts and spray window advisories.'}
                  </span>
                </label>
              </div>

              <button
                type="submit"
                className="topbar-btn"
                style={{
                  background: 'var(--accent-terracotta)',
                  color: '#ffffff',
                  justifyContent: 'center',
                  fontWeight: 600,
                  padding: '0.65rem',
                  borderColor: 'transparent',
                  marginTop: '0.25rem'
                }}
              >
                <span>{lang === 'mr' ? 'बदल जतन करा' : 'Save Profile Preferences'}</span>
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

