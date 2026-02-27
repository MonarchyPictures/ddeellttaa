import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Shield, Zap, Globe, AlertCircle, CheckCircle2 } from 'lucide-react';

const Settings = () => {
  const [scrapers, setScrapers] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(null);

  const fetchScrapers = async () => {
    try {
      // Try relative URLs first
      const urls = ['/api/scrapers/', '/api/scrapers'];
      let response = null;
      let lastError = null;

      for (const url of urls) {
        try {
          console.log('[Settings] Fetching:', url);
          const res = await fetch(url, {
            headers: { 'Accept': 'application/json' }
          });
          if (res.ok) {
            response = res;
            break;
          }
        } catch (e) {
          lastError = e;
          console.log('[Settings] Failed:', url);
        }
      }

      if (!response) {
        throw lastError || new Error('Failed to fetch from all URLs');
      }

      const data = await response.json();
      console.log('[Settings] Data received:', Object.keys(data));

      // The API returns { scraperName: { ... } }
      // Validate and normalize
      const normalized = {};
      for (const [name, scraperData] of Object.entries(data)) {
        if (typeof scraperData === 'object' && scraperData !== null) {
          normalized[name] = {
            enabled: Boolean(scraperData.enabled),
            core: Boolean(scraperData.core),
            mode: scraperData.mode || 'production',
            cost: scraperData.cost || 'free',
            noise: scraperData.noise || 'low',
            categories: scraperData.categories || ['general'],
            metrics: scraperData.metrics || {}
          };
        }
      }

      console.log('[Settings] Normalized:', Object.keys(normalized));
      setScrapers(normalized);
      setError(null);
    } catch (err) {
      console.error('[Settings] Error:', err);
      setError('Connection error: ' + (err?.message || 'Unknown'));
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
      const newState = !currentState;
      const res = await fetch(`/api/scrapers/toggle?name=${name}&enabled=${newState}`, {
        method: 'POST',
        headers: { 'x-role': 'user' }
      });

      if (res.ok) {
        setScrapers(prev => ({
          ...prev,
          [name]: { ...prev[name], enabled: newState }
        }));
      } else {
        alert('Failed to update scraper');
      }
    } catch (err) {
      alert('Network error');
    } finally {
      setUpdating(null);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-black">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const scraperEntries = Object.entries(scrapers);
  console.log('[Settings] Rendering scrapers:', scraperEntries.length);

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

        {/* Debug Info */}
        <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-2xl">
          <p className="text-yellow-500 text-xs font-mono">DEBUG: Found {scraperEntries.length} scrapers</p>
        </div>

        {/* Scrapers Section */}
        <section className="space-y-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Zap className="text-yellow-500" size={20} />
              <h3 className="text-lg font-black uppercase tracking-widest italic">Signal Scrapers</h3>
            </div>
            <span className="text-[10px] font-black bg-white/5 px-3 py-1 rounded-full text-white/40 uppercase tracking-widest">
              {scraperEntries.length} Available
            </span>
          </div>

          {scraperEntries.length === 0 ? (
            <div className="p-8 text-center border border-white/10 rounded-2xl">
              <p className="text-white/40">No scrapers found. Check connection.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {scraperEntries.map(([name, data]) => (
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
              ))}
            </div>
          )}
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
