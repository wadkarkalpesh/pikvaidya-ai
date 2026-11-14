import React, { useState } from 'react';
import { X, UserCheck, Send, CheckCircle2 } from 'lucide-react';

export default function KvkModal({
  isOpen,
  onClose,
  diagResult,
  district,
  lang
}) {
  const [farmerName, setFarmerName] = useState('');
  const [mobileNumber, setMobileNumber] = useState('');
  const [remarks, setRemarks] = useState('');
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen || !diagResult) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      onClose();
    }, 2200);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <UserCheck size={20} color="var(--accent-terracotta)" />
            <h3>{lang === 'mr' ? 'KVK कृषी तज्ज्ञ पडताळणी' : 'KVK Expert Escalation Referral'}</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {submitted ? (
            <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
              <CheckCircle2 size={48} color="var(--accent-green)" style={{ margin: '0 auto 0.75rem auto' }} />
              <h4 style={{ fontSize: '1.1rem', color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                {lang === 'mr' ? 'प्रकरण यशस्वीरित्या पाठवले गेले!' : 'Case Successfully Escalated!'}
              </h4>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {lang === 'mr'
                  ? 'आपला अहवाल आणि Grad-CAM पुरावे स्थानिक कृषी विज्ञान केंद्रातील तज्ज्ञांना पाठवले आहेत. लवकरच संपर्क केला जाईल.'
                  : 'Your diagnostic evidence, leaf photo, and Grad-CAM saliency have been forwarded to the District KVK Pathologist.'}
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {/* Diagnosis Summary Pill */}
              <div style={{ background: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontSize: '0.8125rem' }}>
                <div><strong>Crop:</strong> {diagResult.crop?.toUpperCase()}</div>
                <div><strong>AI Diagnosis:</strong> {diagResult.predicted_class} ({(diagResult.confidence * 100).toFixed(1)}%)</div>
                <div><strong>District:</strong> {district?.toUpperCase() || 'MAHARASHTRA'}</div>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {lang === 'mr' ? 'शेतकऱ्याचे नाव (Farmer Name)' : 'Farmer Name'}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Patil"
                  value={farmerName}
                  onChange={(e) => setFarmerName(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {lang === 'mr' ? 'मोबाईल क्रमांक (Mobile Number)' : 'Mobile Number'}
                </label>
                <input
                  type="tel"
                  required
                  placeholder="e.g. 98220XXXXX"
                  value={mobileNumber}
                  onChange={(e) => setMobileNumber(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {lang === 'mr' ? 'पानावरील लक्षणे / तज्ज्ञांसाठी नोंद (Symptoms / Remarks)' : 'Field Observations & Symptoms'}
                </label>
                <textarea
                  rows={3}
                  placeholder="Describe foliar symptoms, spread rate, or recent irrigation/fertilizer applications..."
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-medium)', fontSize: '0.85rem', resize: 'vertical' }}
                />
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
                  marginTop: '0.5rem'
                }}
              >
                <Send size={15} />
                <span>{lang === 'mr' ? 'KVK कडे पाठवा' : 'Send for KVK Expert Review'}</span>
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

