import React, { useState, useEffect } from 'react';
import getApiUrl, { getApiKey } from '../config';
import { Settings as SettingsIcon, Shield, Zap, Globe, AlertCircle, CheckCircle2 } from 'lucide-react';

const Settings = () => {
  const [scrapers, setScrapers] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(null);

  const resolveApiBaseUrl = () => {
    const apiUrl = getApiUrl();
    if (apiUrl.startsWith('http://') || apiUrl.startsWith('https://')) {
      return apiUrl.replace(/\/$/, '');
    }
    if (import.meta.env.DEV) {
      return `http://localhost:8001${apiUrl}`.replace(/\/$/, '');
    }
    return `${window.location.protocol}//${window.location.host}${apiUrl}`.replace(/\/$/, '');
  };

  const normalizeScrapersPayload = (payload) => {
    if (!payload) return {};
    if (Array.isArray(payload)) {
      return payload.reduce((acc, item, idx) => {
        const name = item?.name || item?.id || `Scraper${idx + 1}`;
        acc[name] = {
          enabled: Boolean(item?.enabled),
          core: Boolean(item?.core),
          mode: item?.mode || 'production',
          cost: item?.cost || 'free',
          noise: item?.noise || 'low',
          categories: item?.categories || ['general'],
          metrics: item?.metrics || {}
        };
        return acc;
      }, {});
    }
    if (payload.scrapers && typeof payload.scrapers === 'object') return payload.scrapers;
    if (payload.data && typeof payload.data === 'object') return payload.data;
    return typeof payload === 'object' ? payload : {};
  };

  const fetchScrapers = async () => {
    try {
      const apiUrl = resolveApiBaseUrl();
      const apiKey = getApiKey();
      const res = await fetch(`${apiUrl}/scrapers/`, {
        headers: { 'X-API-Key': apiKey }
      });
      if (res.ok) {
        const data = await res.json();
        const normalized = normalizeScrapersPayload(data);
        setScrapers(normalized);
        setError(null);
      } else {
        setError(`Failed to fetch scrapers (${res.status})`);
      }
    } catch (err) {
      setError(`Connection error${err?.message ? `: ${err.message}` : ''}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScrapers();
  }, []);

  const toggleScraper = async (name, currentState) => {
    setUpdating(name);
    try {
      const apiUrl = resolveApiBaseUrl();
      const apiKey = getApiKey();
      const newState = !currentState;
      
      const res = await fetch(`${apiUrl}/scrapers/toggle?name=${name}&enabled=${newState}`, {
        method: 'POST',
        headers: { 
          'X-API-Key': apiKey,
          'x-role': 'user'
        }
      });

      if (res.ok) {
        setScrapers(prev => ({
          ...prev,
          [name]: { ...prev[name], enabled: newState }
        }));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to update scraper");
      }
    } catch (err) {
      alert("Network error updating scraper");
    } finally {
      setUpdating(null);
    }
  };

  if (loading) return (
    <div className="flex-1 flex items-center justify-center bg-black">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  );

  return (
    <div className="flex-1 overflow-y-auto bg-black p-4 md:p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-center gap-4 text-center md:text-left">
          <div className="p-3 bg-blue-600/20 rounded-2xl">
            <SettingsIcon className="text-blue-500" size={32} />
          </div>
          <div>
            <h2 className="text-xl md:text-3xl font-black italic tracking-tighter uppercase">Settings</h2>
            <p className="text-white/40 text-sm font-bold tracking-widest uppercase">System Configuration • Kenya Vehicles</p>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center gap-3 text-red-500">
            <AlertCircle size={20} />
            <span className="font-bold text-sm uppercase tracking-tight">{error}</span>
          </div>
        )}

        {/* Scrapers Section */}
        <section className="space-y-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Zap className="text-yellow-500" size={20} />
              <h3 className="text-lg font-black uppercase tracking-widest italic">Signal Scrapers</h3>
            </div>
            <span className="text-[10px] font-black bg-white/5 px-3 py-1 rounded-full text-white/40 uppercase tracking-widest">
              {Object.keys(scrapers).length} Available
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(scrapers).map(([name, data]) => (
              <div key={name} className={`p-5 rounded-3xl border transition-all duration-300 ${data.enabled ? 'bg-white/5 border-white/10' : 'bg-black border-white/5 opacity-60'}`}>
                <div className="flex items-start justify-between mb-4">
                  <div className="space-y-1">
                    <h4 className="font-black text-sm uppercase tracking-tight flex items-center gap-2">
                      {name.replace('Scraper', '')}
                      {data.core && <Shield size={12} className="text-blue-500" title="Core Scraper" />}
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md ${data.cost === 'free' ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'}`}>
                        {data.cost}
                      </span>
                      <span className="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md bg-white/5 text-white/40">
                        {data.noise} noise
                      </span>
                      {data.mode === 'bootstrap' && (
                        <span className="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-500">
                          Bootstrap
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <button
                    onClick={() => toggleScraper(name, data.enabled)}
                    disabled={updating === name || data.core}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${data.enabled ? 'bg-blue-600' : 'bg-white/10'} ${data.core ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${data.enabled ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-[10px] text-white/40 font-bold uppercase tracking-widest">
                    <Globe size={12} />
                    <span>Categories: {data.categories ? data.categories.join(', ') : 'All'}</span>
                  </div>
                  
                  {data.metrics && (
                    <div className="grid grid-cols-3 gap-2 pt-3 border-t border-white/5">
                      <div className="text-center">
                        <div className="text-[10px] font-black text-white/20 uppercase tracking-tighter">Leads</div>
                        <div className="text-xs font-bold">{data.metrics.leads_found || 0}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-[10px] font-black text-white/20 uppercase tracking-tighter">Success</div>
                        <div className="text-xs font-bold text-green-500">{data.metrics.success_rate || '0%'}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-[10px] font-black text-white/20 uppercase tracking-tighter">Speed</div>
                        <div className="text-xs font-bold">{data.metrics.avg_speed || '0s'}</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Info Card */}
        <div className="p-6 bg-blue-600/10 border border-blue-600/20 rounded-3xl flex gap-4">
          <CheckCircle2 className="text-blue-500 shrink-0" size={24} />
          <div className="space-y-1">
            <p className="text-xs font-bold text-blue-200 uppercase tracking-wide">Optimization Tip</p>
            <p className="text-sm text-white/60">Core scrapers like Google Maps and Classifieds cannot be disabled to ensure minimum signal coverage for the Kenya Vehicles market.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
