import React, { useRef } from 'react';
import {
  Camera,
  Image as ImageIcon,
  ArrowUp,
  MapPin,
  Cpu,
  X,
  Sparkles,
  ChevronDown
} from 'lucide-react';

export default function InputBar({
  text,
  onTextChange,
  onSend,
  isLoading,
  selectedImage,
  imagePreview,
  onImageChange,
  onRemoveImage,
  crop,
  onCropChange,
  district,
  onDistrictChange,
  districtsList,
  gpsLocation,
  onUseGps,
  useEdgeAi,
  onToggleEdgeAi,
  lang,
  t
}) {
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const cropNames = {
    sugarcane: lang === 'mr' ? 'ऊस (Sugarcane)' : 'Sugarcane',
    tomato: lang === 'mr' ? 'टोमॅटो (Tomato)' : 'Tomato',
    onion: lang === 'mr' ? 'कांदा (Onion)' : 'Onion',
    auto: lang === 'mr' ? '🤖 स्वयंचलित (Auto)' : '🤖 Auto Detect'
  };

  return (
    <div className="claude-input-fixed-container">
      <div className="claude-input-box">
        {/* Image Attachment Preview Strip */}
        {imagePreview && (
          <div className="attachment-preview-strip">
            <img src={imagePreview} alt="Selected leaf" className="attachment-thumb" />
            <div className="attachment-meta">
              <strong>{selectedImage ? selectedImage.name : 'leaf_sample.jpg'}</strong>
              <span>
                {useEdgeAi
                  ? '⚡ Edge WASM INT8 Ready'
                  : '☁️ Cloud PyTorch + Grad-CAM Ready'}
              </span>
            </div>
            <button
              className="attachment-remove-btn"
              onClick={onRemoveImage}
              title="Remove image"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Text Input Area */}
        <textarea
          ref={textareaRef}
          rows={1}
          className="claude-textarea"
          placeholder={
            selectedImage
              ? (lang === 'mr'
                  ? 'पानाचे लक्षण किंवा फवारणीबद्दल विचारा...'
                  : 'Ask about symptoms or click send for diagnosis...')
              : (lang === 'mr'
                  ? 'शेती, पीक रोग किंवा फवारणीबद्दल विचारा (मराठी/हिंदी/EN)...'
                  : 'Ask an agronomic question or upload leaf photo...')
          }
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        {/* Bottom Toolbar Controls */}
        <div className="input-controls-row">
          <div className="input-left-pills">
            {/* Hidden File Input */}
            <input
              type="file"
              ref={fileInputRef}
              accept="image/jpeg,image/png,image/webp"
              onChange={onImageChange}
              style={{ display: 'none' }}
            />

            {/* Photo / Attachment Button */}
            <button
              type="button"
              className={`pill-select-btn ${selectedImage ? 'active' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              title="Upload leaf photo (JPEG, PNG, WEBP)"
            >
              <Camera size={14} />
              <span>{selectedImage ? (lang === 'mr' ? 'फोटो निवडला' : 'Photo Attached') : (lang === 'mr' ? 'फोटो जोडा' : 'Add Photo')}</span>
            </button>

            {/* Crop Selector Pill */}
            <div className="pill-select-btn">
              <span>🌾</span>
              <select
                className="pill-dropdown"
                value={crop}
                onChange={(e) => onCropChange(e.target.value)}
              >
                <option value="auto">{cropNames.auto}</option>
                <option value="sugarcane">{cropNames.sugarcane}</option>
                <option value="tomato">{cropNames.tomato}</option>
                <option value="onion">{cropNames.onion}</option>
              </select>
            </div>

            {/* District / GPS Selector Pill */}
            <div className="pill-select-btn">
              <MapPin size={13} />
              {gpsLocation ? (
                <span onClick={onUseGps} title="GPS Active" style={{ cursor: 'pointer', fontWeight: 600 }}>
                  GPS ({gpsLocation.lat.toFixed(1)}, {gpsLocation.lon.toFixed(1)})
                </span>
              ) : (
                <select
                  className="pill-dropdown"
                  value={district}
                  onChange={(e) => onDistrictChange(e.target.value)}
                >
                  {districtsList.map((d) => (
                    <option key={d.id} value={d.id}>
                      {lang === 'mr' ? d.name_mr : d.name}
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
              )}
            </div>

            {/* Edge AI Toggle Pill */}
            <button
              type="button"
              className={`pill-select-btn ${useEdgeAi ? 'active' : ''}`}
              onClick={onToggleEdgeAi}
              title="Toggle between on-device WebAssembly INT8 and Cloud PyTorch inference"
            >
              <Cpu size={13} />
              <span>{useEdgeAi ? '⚡ Edge WASM' : '☁️ Cloud'}</span>
            </button>
          </div>

          {/* Send / Diagnose Arrow Button */}
          <button
            type="button"
            className="claude-send-btn"
            onClick={onSend}
            disabled={isLoading || (!text.trim() && !selectedImage)}
            title={selectedImage ? "Run leaf diagnosis" : "Send message"}
          >
            {isLoading ? (
              <span style={{ fontSize: '0.75rem' }}>⏳</span>
            ) : (
              <ArrowUp size={18} strokeWidth={2.4} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

