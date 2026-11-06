import React, { useState, useEffect, useRef } from 'react';
import { translations } from './i18n/translations';

export default function App() {
  const [lang, setLang] = useState('mr'); // Default Marathi for regional farmers
  const [crop, setCrop] = useState('sugarcane');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [diagResult, setDiagResult] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [district, setDistrict] = useState('pune');
  const [districtsList, setDistrictsList] = useState([]);
  const [gpsLocation, setGpsLocation] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [forecastTab, setForecastTab] = useState('hourly'); // 'hourly' | 'daily'

  // RAG Chatbot state
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const chatBottomRef = useRef(null);

  const t = translations[lang] || translations.en;

  // Initial welcome message for chat
  useEffect(() => {
    const welcomeText = lang === 'mr'
      ? "नमस्कार! मी पिकवैद्य AI कृषी मित्र आहे. ऊस, टोमॅटो व कांदा पिकांवरील रोग, औषधांची मात्रा (ICAR/CIBRC) किंवा हवामान फवारणीबद्दल विचारा."
      : lang === 'hi'
      ? "नमस्ते! मैं पिकवैद्य AI कृषि सहायक हूं। गन्ना, टमाटर और प्याज की बीमारियों, कीटनाशक की मात्रा या मौसम अनुकूलता के बारे में पूछें।"
      : "Hello! I am PikVaidya AI Agricultural Assistant. Ask me anything about sugarcane, tomato, and onion pathology, ICAR/CIBRC chemical dosages, or weather spray suitability.";

    setChatMessages([
      { sender: 'bot', text: welcomeText, sources: [] }
    ]);
  }, [lang]);

  // Fetch Maharashtra districts on load
  useEffect(() => {
    async function fetchDistricts() {
      try {
        const res = await fetch('/api/v1/weather/locations');
        if (res.ok) {
          const data = await res.json();
          setDistrictsList(data.districts || []);
        }
      } catch (err) {
        console.warn('Failed to fetch districts:', err);
      }
    }
    fetchDistricts();
  }, []);

  // Fetch weather when district or GPS changes
  useEffect(() => {
    async function loadWeather() {
      setWeatherLoading(true);
      try {
        let url = '';
        if (gpsLocation) {
          url = `/api/v1/weather/current?lat=${gpsLocation.lat}&lon=${gpsLocation.lon}&persist=true`;
        } else {
          url = `/api/v1/weather/current?district=${district}&persist=true`;
        }
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setWeatherData(data);
        }
      } catch (err) {
        console.warn('Weather fetch error:', err);
      } finally {
        setWeatherLoading(false);
      }
    }
    loadWeather();
  }, [district, gpsLocation]);

  const handleUseGps = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
      },
      (err) => {
        alert("GPS Error: " + err.message);
      }
    );
  };


  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      setImagePreview(URL.createObjectURL(file));
      setDiagResult(null);
    }
  };

  const handleDiagnose = async () => {
    if (!selectedImage) return;
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', selectedImage);
      formData.append('crop', crop);
      formData.append('generate_gradcam', 'true');
      formData.append('save_heatmap', 'true');

      const response = await fetch('/api/v1/diagnose/predict', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Diagnosis failed');
      }

      const data = await response.json();
      setDiagResult(data);

      // Also auto-inject finding into chat assistant context
      const findingMsg = lang === 'mr'
        ? `[सिस्टम सूचना] पानाचे निदान झाले: ${data.predicted_class} (विश्वासार्हता: ${(data.confidence * 100).toFixed(1)}%).`
        : `[System Notice] Image diagnosed: ${data.predicted_class} (Confidence: ${(data.confidence * 100).toFixed(1)}%).`;

      setChatMessages(prev => [...prev, { sender: 'bot', text: findingMsg, sources: [] }]);
    } catch (err) {
      alert(`Diagnosis Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (textToSend) => {
    const query = textToSend || chatInput;
    if (!query.trim() || chatLoading) return;

    // Add user message
    setChatMessages(prev => [...prev, { sender: 'user', text: query }]);
    if (!textToSend) setChatInput('');
    setChatLoading(true);

    try {
      const payload = {
        message: query,
        language: lang,
        session_id: sessionId,
        diagnostic_context: diagResult ? {
          crop_name: crop,
          predicted_disease: diagResult.predicted_class,
          confidence: diagResult.confidence,
        } : null,
        weather_context: weatherData?.current_telemetry || null,
      };

      const res = await fetch('/api/v1/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error('Assistant query failed');

      const data = await res.json();
      setSessionId(data.session_id);
      setChatMessages(prev => [
        ...prev,
        {
          sender: 'bot',
          text: data.reply,
          sources: data.sources || [],
          recommendations: data.key_recommendations || []
        }
      ]);
    } catch (err) {
      setChatMessages(prev => [
        ...prev,
        { sender: 'bot', text: `Error: ${err.message}`, sources: [] }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Navigation */}
      <nav className="navbar">
        <div className="navbar-container">
          <div className="brand">
            <div className="brand-icon">🌿</div>
            <div className="brand-text">
              <h1>{t.appTitle}</h1>
              <p>{t.appSubtitle}</p>
            </div>
          </div>

          <div className="nav-actions">
            <select
              className="lang-select"
              value={lang}
              onChange={(e) => setLang(e.target.value)}
            >
              <option value="mr">मराठी (Marathi)</option>
              <option value="en">English</option>
              <option value="hi">हिंदी (Hindi)</option>
            </select>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {/* Hero Banner */}
        <section className="hero-card">
          <div className="hero-text">
            <h2>{t.appSubtitle}</h2>
            <p>
              {lang === 'mr'
                ? "कृत्रिम बुद्धिमत्ता (PyTorch EfficientNet-B0 / MobileNetV3) आणि सूक्ष्म हवामान माहितीचा वापर करून शेतकरी बांधवांना थेट अचूक, वैधानिक व सुरक्षित शेती सल्ला."
                : "Combining edge-to-cloud PyTorch deep learning with microclimate weather telemetry to deliver grounded, explainable, and legal farming advisories."}
            </p>
          </div>
          <div className="hero-badges">
            <div className="hero-badge">⚡ Calibrated PyTorch XAI</div>
            <div className="hero-badge">🌦️ Open-Meteo Weather Gating</div>
            <div className="hero-badge">📜 ICAR & CIBRC Grounded</div>
          </div>
        </section>

        {/* Dashboard Grid */}
        <div className="dashboard-grid">
          {/* Left Column: Image Upload & Crop Switcher */}
          <div className="left-col">
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <span>🌾</span> {t.selectCrop}
                </h3>
              </div>

              {/* Crop Tabs */}
              <div className="crop-tabs">
                <button
                  className={`crop-tab ${crop === 'sugarcane' ? 'active' : ''}`}
                  onClick={() => { setCrop('sugarcane'); setDiagResult(null); }}
                >
                  🍬 {t.sugarcane}
                </button>
                <button
                  className={`crop-tab ${crop === 'tomato' ? 'active' : ''}`}
                  onClick={() => { setCrop('tomato'); setDiagResult(null); }}
                >
                  🍅 {t.tomato}
                </button>
                <button
                  className={`crop-tab ${crop === 'onion' ? 'active' : ''}`}
                  onClick={() => { setCrop('onion'); setDiagResult(null); }}
                >
                  🧅 {t.onion}
                </button>
              </div>

              {/* Upload Dropzone */}
              <label className="dropzone">
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleImageChange}
                  style={{ display: 'none' }}
                />
                <div className="dropzone-icon">📷</div>
                <h4>{t.uploadTitle}</h4>
                <p>{t.uploadSubtitle}</p>
              </label>

              {/* Image Preview */}
              {imagePreview && (
                <div className="preview-container">
                  <img src={imagePreview} alt="Selected Leaf" className="preview-img" />
                </div>
              )}

              {/* Action Button */}
              <button
                className="btn-primary"
                onClick={handleDiagnose}
                disabled={!selectedImage || loading}
              >
                {loading ? t.diagnosing : t.diagnoseButton}
              </button>
            </div>

            {/* Weather Microclimate Card */}
            <div className="card">
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 className="card-title">
                  <span>🌦️</span> {t.weatherTitle}
                </h3>
                {weatherLoading && <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>⏳ Loading...</span>}
              </div>

              {/* District & GPS Selector */}
              <div className="weather-location-bar">
                <select
                  className="location-select"
                  value={gpsLocation ? 'custom_gps' : district}
                  onChange={(e) => {
                    if (e.target.value !== 'custom_gps') {
                      setGpsLocation(null);
                      setDistrict(e.target.value);
                    }
                  }}
                >
                  {gpsLocation && <option value="custom_gps">📍 Farm GPS ({gpsLocation.lat.toFixed(2)}, {gpsLocation.lon.toFixed(2)})</option>}
                  {districtsList.map((d) => (
                    <option key={d.id} value={d.id}>
                      {lang === 'mr' ? d.name_mr : lang === 'hi' ? d.name_hi : d.name} (Maharashtra)
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
                <button
                  className={`gps-btn ${gpsLocation ? 'active' : ''}`}
                  onClick={handleUseGps}
                  title="Detect GPS location"
                >
                  📍 {t.useGps}
                </button>
              </div>

              {weatherData && (
                <>
                  {/* Weather Alerts if any */}
                  {weatherData.alerts && weatherData.alerts.length > 0 && (
                    <div className="weather-alerts-container">
                      {weatherData.alerts.map((alt, idx) => (
                        <div key={idx} className={`weather-alert-card ${alt.severity}`}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                            <span>⚠️ {lang === 'mr' ? alt.title_mr || alt.title : lang === 'hi' ? alt.title_hi || alt.title : alt.title}</span>
                            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase' }}>{alt.severity}</span>
                          </div>
                          <p style={{ margin: 0, fontSize: '0.75rem' }}>
                            {lang === 'mr' ? alt.description_mr || alt.description : lang === 'hi' ? alt.description_hi || alt.description : alt.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Spray Window Banner */}
                  {weatherData.spray_window && (
                    <div className={`weather-status-box ${
                      weatherData.spray_window.is_safe_to_spray || weatherData.spray_window.is_suitable ? 'optimal' : 'cancelled'
                    }`}>
                      <div>
                        <strong>
                          {weatherData.spray_window.is_safe_to_spray ? '✅ ' + t.optimalSpray : '⛔ ' + t.cancelledSpray}
                        </strong>
                        <p style={{ fontSize: '0.8rem', marginTop: '0.2rem', marginBottom: 0 }}>
                          {weatherData.spray_window.summary?.[lang] ||
                           weatherData.spray_window.summary?.en ||
                           weatherData.spray_window.summary_en ||
                           weatherData.spray_window.advisory_recommendation?.[lang] ||
                           weatherData.spray_window.advisory_recommendation?.en}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Atmospheric Telemetry Grid */}
                  <div className="weather-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                    <div className="weather-item">
                      <span>Temp</span>
                      <strong>
                        {weatherData.current?.temperature_c ?? weatherData.current_telemetry?.temperature_c ?? weatherData.temperature_c ?? '--'}°C
                      </strong>
                      <span style={{ fontSize: '0.65rem', color: 'var(--slate-400)' }}>
                        {t.apparentTemp}: {weatherData.current?.apparent_temperature_c ?? '--'}°C
                      </span>
                    </div>

                    <div className="weather-item">
                      <span>Humidity</span>
                      <strong>
                        {weatherData.current?.relative_humidity_pct ?? weatherData.current_telemetry?.relative_humidity_pct ?? weatherData.relative_humidity_pct ?? '--'}%
                      </strong>
                      <span style={{ fontSize: '0.65rem', color: 'var(--slate-400)' }}>
                        {weatherData.spray_window?.fungal_risk_level ? `Risk: ${weatherData.spray_window.fungal_risk_level}` : ''}
                      </span>
                    </div>

                    <div className="weather-item">
                      <span>Wind</span>
                      <strong>
                        {weatherData.current?.wind_speed_kmh ?? weatherData.current_telemetry?.wind_speed_kmh ?? weatherData.wind_speed_kmh ?? '--'} km/h
                      </strong>
                      <span style={{ fontSize: '0.65rem', color: 'var(--slate-400)' }}>
                        Gust: {weatherData.current?.wind_gusts_kmh ?? '--'} km/h
                      </span>
                    </div>

                    <div className="weather-item">
                      <span>Rain Prob</span>
                      <strong>
                        {weatherData.current?.precipitation_probability_6h ?? weatherData.current_telemetry?.precipitation_probability_6h ?? weatherData.precipitation_probability_6h ?? '0'}%
                      </strong>
                      <span style={{ fontSize: '0.65rem', color: 'var(--slate-400)' }}>
                        Rate: {weatherData.current?.precipitation_mm ?? 0} mm/h
                      </span>
                    </div>

                    <div className="weather-item">
                      <span>{t.surfacePressure}</span>
                      <strong>
                        {weatherData.current?.surface_pressure_hpa ?? 1013} hPa
                      </strong>
                    </div>

                    <div className="weather-item">
                      <span>{t.cloudCover}</span>
                      <strong>
                        {weatherData.current?.cloud_cover_pct ?? 0}%
                      </strong>
                    </div>
                  </div>

                  {/* Modeled Soil Moisture Telemetry */}
                  {weatherData.soil && (
                    <div className="soil-telemetry-box">
                      <div className="soil-header">
                        <h4>🌱 {t.soilMoistureTitle}</h4>
                        <span className="modeled-badge">🛰️ {t.modeledTag}</span>
                      </div>
                      <div className="soil-metric-row">
                        <span>
                          <strong>{weatherData.soil.soil_moisture_percentage}%</strong> (volumetric)
                        </span>
                        <span>
                          Temp: <strong>{weatherData.soil.soil_temperature_c}°C</strong>
                        </span>
                        <span className={`soil-status-pill ${weatherData.soil.moisture_status}`}>
                          {weatherData.soil.moisture_status}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Forecast Strip (24h / 7d toggle) */}
                  {(weatherData.hourly_24h?.length > 0 || weatherData.daily_7d?.length > 0) && (
                    <div className="forecast-strip-container">
                      <div className="forecast-tabs">
                        <button
                          className={`forecast-tab-btn ${forecastTab === 'hourly' ? 'active' : ''}`}
                          onClick={() => setForecastTab('hourly')}
                        >
                          🕒 {t.forecast24h}
                        </button>
                        <button
                          className={`forecast-tab-btn ${forecastTab === 'daily' ? 'active' : ''}`}
                          onClick={() => setForecastTab('daily')}
                        >
                          📅 {t.forecast7d}
                        </button>
                      </div>

                      {forecastTab === 'hourly' && weatherData.hourly_24h && (
                        <div className="hourly-scroll-strip">
                          {weatherData.hourly_24h.map((h, idx) => (
                            <div key={idx} className="hourly-mini-card">
                              <div className="hour-time">{h.time ? h.time.substring(11, 16) : `+${idx}h`}</div>
                              <div className="hour-temp">{h.temperature_c}°</div>
                              <div className="hour-rain">💧 {h.precipitation_probability}%</div>
                            </div>
                          ))}
                        </div>
                      )}

                      {forecastTab === 'daily' && weatherData.daily_7d && (
                        <div className="daily-forecast-list">
                          {weatherData.daily_7d.map((d, idx) => (
                            <div key={idx} className="daily-row">
                              <span className="day-name">{d.date}</span>
                              <span className="day-temps">{d.temp_max_c}° / {d.temp_min_c}°C</span>
                              <span className="day-rain">💧 {d.precipitation_probability_max}% ({d.precipitation_sum_mm}mm)</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Attribution & Location Footer */}
                  <div className="weather-footer-attribution">
                    <span>{weatherData.location_name || 'Maharashtra'}</span>
                    <span>{t.dataSourceTag}</span>
                  </div>
                </>
              )}
            </div>

          </div>

          {/* Right Column: Diagnostic XAI Results & Advisory */}
          <div className="right-col">
            {diagResult ? (
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <span>🔍</span> {t.resultsTitle}
                  </h3>
                  <span className="confidence-badge">
                    {t.calibratedConfidence}: {(diagResult.confidence * 100).toFixed(1)}%
                  </span>
                </div>

                {/* XAI Side-by-Side Visuals */}
                <div className="xai-grid">
                  <div className="xai-panel">
                    <div className="xai-panel-header">{t.originalLeaf}</div>
                    <img src={imagePreview} alt="Original Leaf" />
                  </div>
                  <div className="xai-panel">
                    <div className="xai-panel-header">{t.gradcamOverlay}</div>
                    <img
                      src={diagResult.heatmap_path ? `/${diagResult.heatmap_path}` : imagePreview}
                      alt="Grad-CAM Overlay"
                    />
                  </div>
                </div>

                {/* Metrics Banner */}
                <div className="metrics-banner">
                  <div>
                    <div className="diag-name">{diagResult.predicted_class}</div>
                    <div className="diag-sub">Crop: {diagResult.crop.toUpperCase()} | Model: {diagResult.model_version}</div>
                  </div>
                  {diagResult.details?.severity && (
                    <div className="hero-badge" style={{ background: '#059669', color: '#fff' }}>
                      {t.severityLevel}: {diagResult.details.severity} ({diagResult.details.affected_area_percentage?.toFixed(1)}%)
                    </div>
                  )}
                </div>

                {/* Context-Aware Advisory */}
                {diagResult.details?.contextual_advisory && (
                  <div className="advisory-section">
                    <h4 className="advisory-title">
                      <span>📘</span> {t.advisoryTitle}
                    </h4>
                    <div className="advisory-body">
                      <p>
                        {diagResult.details.contextual_advisory.disease_overview?.[lang] ||
                         diagResult.details.contextual_advisory.disease_overview?.en}
                      </p>
                    </div>

                    {/* Cultural Practices */}
                    {diagResult.details.contextual_advisory.cultural_practices?.length > 0 && (
                      <div style={{ marginBottom: '1rem' }}>
                        <h5 style={{ fontSize: '0.85rem', color: '#064e3b', fontWeight: 700, marginBottom: '0.35rem' }}>
                          🌱 {t.culturalMethods}:
                        </h5>
                        <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: '#334155' }}>
                          {diagResult.details.contextual_advisory.cultural_practices.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* CIBRC Chemical Prescriptions */}
                    {diagResult.details.contextual_advisory.chemical_prescriptions?.map((chem, idx) => (
                      <div key={idx} className="chemical-card">
                        <h5>🧪 {chem.chemical_name}</h5>
                        <p><strong>Dose:</strong> {chem.dosage} ({chem.dilution})</p>
                        <p><strong>Method:</strong> {chem.application_method}</p>
                        {chem.phi_days && (
                          <div className="phi-badge">⏳ Pre-Harvest Interval (PHI): {chem.phi_days} Days</div>
                        )}
                      </div>
                    ))}

                    {/* Statutory Notice */}
                    <div className="statutory-notice">
                      ⚖️ {diagResult.details.contextual_advisory.statutory_disclaimer?.[lang] ||
                          diagResult.details.contextual_advisory.statutory_disclaimer?.en}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem', color: '#64748b' }}>
                <div style={{ fontSize: '3rem', marginBottom: '0.75rem' }}>🌿</div>
                <h3 style={{ color: '#1e293b', marginBottom: '0.5rem' }}>Ready for Crop Leaf Diagnosis</h3>
                <p style={{ maxWidth: '420px', margin: '0 auto', fontSize: '0.9rem' }}>
                  Upload a crop leaf photograph on the left to inspect native PyTorch inference, Grad-CAM visual heatmaps, and ICAR/CIBRC recommendations.
                </p>
              </div>
            )}

            {/* Embedded Multilingual RAG Assistant Drawer */}
            <div className="rag-chat-drawer">
              <div className="chat-header">
                <span>🤖</span> {t.chatTitle}
              </div>

              {/* Chat Message List */}
              <div className="chat-messages">
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`chat-msg ${msg.sender}`}>
                    <p>{msg.text}</p>
                    {msg.sources?.length > 0 && (
                      <div>
                        {msg.sources.map((s, si) => (
                          <span key={si} className="citation">
                            📚 {s.source_name || s.organization}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {chatLoading && (
                  <div className="chat-msg bot">
                    <em>{t.thinking}</em>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>

              {/* Quick Prompt Chips */}
              <div className="chat-chips">
                {t.quickQuestions.map((q, qi) => (
                  <button key={qi} className="chip-btn" onClick={() => handleSendMessage(q)}>
                    {q}
                  </button>
                ))}
              </div>

              {/* Chat Input Bar */}
              <div className="chat-input-row">
                <input
                  type="text"
                  className="chat-input"
                  placeholder={t.chatPlaceholder}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                />
                <button
                  className="chat-send-btn"
                  onClick={() => handleSendMessage()}
                  disabled={chatLoading}
                >
                  {t.send}
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

