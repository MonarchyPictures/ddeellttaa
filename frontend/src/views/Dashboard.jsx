// frontend/src/views/Dashboard.jsx
// ============================================================
// UPDATED — Added LiveBuyerFeed section
// ============================================================
// Add this section to your existing Dashboard.jsx
// Place it after the search results grid

import React, { useState, useEffect, useRef } from 'react';
import { Search, Activity, Target, Zap, Radio } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import LeadCard from '../components/LeadCard';
import LiveBuyerFeed from '../components/LiveBuyerFeed';
import { useNotifications } from '../context/NotificationContext';
import {
  API_URL,
  headers,
  fetchWithRetry,
  resolveApiUrl
} from '../utils/api';

const Dashboard = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');
  const [metrics, setMetrics] = useState(null);
  const { isConnected, simulateNotification } = useNotifications();
  const navigate = useNavigate();

  // Test Notification Handler
  const testNotification = () => {
    simulateNotification({
      id: `test_${Date.now()}`,
      buyer_name: "John Kamau",
      title: "Looking for 2BR apartment in Kileleshwa, budget 45k",
      buyer_request_snippet: "Natafuta apartment 2br Kileleshwa area, budget 40-50k monthly. Niko ready to move end of this month. Prefer furnished or semi-furnished. Call me 0712345678",
      phone: "+254712345678",
      contact_phone: "+254712345678",
      whatsapp_url: "https://wa.me/254712345678",
      telegram_username: "johnkamau",
      location: "Kileleshwa, Nairobi",
      source: "Telegram: Kilimani Tenants",
      intent_score: 0.92,
      badge: "HOT",
      price: "KES 40,000-50,000/mo",
      url: "https://t.me/kilimani_tenants/12345",
      ranked_score: 0.88,
      timeline: "immediate"
    });
  };

  // NOTE: Removed auto-fetch of /api/leads on mount.
  // User must search to see leads. This prevents:
  // 1. Override of search results
  // 2. Loading stale data
  // 3. Unnecessary API calls
  // Search flow: POST /api/search → setLeads(response.results)

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError('');
    setSearched(true);
    setMetrics(null);

    try {
      // FRONTEND PIPELINE TRACE
      console.log('[FRONTEND] =============================');
      console.log('[FRONTEND] Search triggered:', searchQuery.trim());
      console.log('[FRONTEND] Request URL:', `${API_URL}/search`);
      
      const requestPayload = {
        query: searchQuery.trim(),
        location: 'Kenya'
      };
      console.log('[FRONTEND] Request payload:', requestPayload);

      const response = await fetchWithRetry(`${API_URL}/search`, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestPayload),
        cache: 'no-store'
      });

      console.log('[FRONTEND] Response status:', response.status);

      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`);
      }

      const data = await response.json();
      
      // DEBUG: Detailed response inspection
      console.log('[FRONTEND] =============================');
      console.log('[FRONTEND] RAW RESPONSE:', data);
      console.log('[FRONTEND] data.results exists:', 'results' in data);
      console.log('[FRONTEND] data.leads exists:', 'leads' in data);
      console.log('[FRONTEND] data.count:', data.count);
      console.log('[FRONTEND] data.status:', data.status);
      console.log('[FRONTEND] data.results type:', typeof data.results);
      console.log('[FRONTEND] data.results is array:', Array.isArray(data.results));
      console.log('[FRONTEND] data.results length:', data.results?.length);
      console.log('[FRONTEND] data.leads length:', data.leads?.length);
      
      // Check if response has the expected structure
      if (data.results && Array.isArray(data.results)) {
        console.log('[FRONTEND] ✓ Using data.results');
      } else if (data.leads && Array.isArray(data.leads)) {
        console.log('[FRONTEND] ✓ Using data.leads (fallback)');
      } else {
        console.error('[FRONTEND] ✗ Neither data.results nor data.leads is a valid array!');
        console.error('[FRONTEND] Available keys:', Object.keys(data));
      }
      
      const results = data.results || data.leads || [];
      
      // Sort by ranked_score
      const sorted = results.sort((a, b) =>
        (b.ranked_score || b.intent_score || 0) - (a.ranked_score || a.intent_score || 0)
      );

      setLeads(sorted);
      setMetrics(data.meta || data.metrics || null);

      if (sorted.length === 0) {
        setError(data.message || 'No buyers found. Try different keywords.');
      }

    } catch (err) {
      console.error('Search error:', err);
      setError('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 bg-black overflow-y-auto pt-20 pb-24">
      <div className="max-w-7xl mx-auto px-4">

        {/* ── Hero + Search ─────────────────────────── */}
        <div className="text-center py-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            Find <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
              Buyers
            </span> For Anything
          </h1>
          <p className="text-white/40 text-sm mb-6">
            Search for what you're selling. We'll find people actively looking to buy it.
          </p>

          <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
            <div className="relative flex items-center">
              <Search className="absolute left-4 w-5 h-5 text-white/30" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="What are you selling? e.g., '2br apartment kileleshwa', 'toyota prado', 'water tank'..."
                className="w-full pl-12 pr-32 py-4 rounded-2xl
                           bg-white/5 border border-white/10 
                           text-white placeholder:text-white/25
                           focus:outline-none focus:border-emerald-500/50
                           text-sm"
              />
              <button
                type="submit"
                disabled={loading || !searchQuery.trim()}
                className="absolute right-2 px-6 py-2.5 rounded-xl
                           bg-gradient-to-r from-emerald-500 to-cyan-500
                           text-black text-sm font-semibold
                           hover:from-emerald-400 hover:to-cyan-400
                           disabled:opacity-30 disabled:cursor-not-allowed
                           transition-all"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <motion.span
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    >
                      ⏳
                    </motion.span>
                    Searching...
                  </span>
                ) : (
                  'Find Buyers'
                )}
              </button>
            </div>
          </form>
        </div>

        {/* ── Search Metrics ────────────────────────── */}
        {metrics && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto mb-6"
          >
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <span className="text-white/30 text-xs">
                📊 {metrics.raw_results || metrics.total_found || 0} signals scanned
              </span>
              <span className="text-white/30 text-xs">
                🎯 {metrics.buyer_count || metrics.buyers_found || metrics.total_shown || leads.length} buyers found
              </span>
              {metrics.platforms_searched && (
                <span className="text-white/30 text-xs">
                  🌐 {metrics.platforms_searched.length} platforms
                </span>
              )}
              {metrics.telegram_results > 0 && (
                <span className="text-emerald-400/60 text-xs">
                  ✈️ {metrics.telegram_results} from Telegram
                </span>
              )}
              {metrics.category && (
                <span className="px-2 py-0.5 rounded-full bg-white/5 text-white/40 text-[10px]">
                  {metrics.category}
                </span>
              )}
            </div>
          </motion.div>
        )}

        {/* ── Error State ───────────────────────────── */}
        {error && searched && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-2xl mx-auto mb-6 text-center"
          >
            <p className="text-white/40 text-sm">{error}</p>
          </motion.div>
        )}

        {/* ── Loading State ─────────────────────────── */}
        {loading && (
          <div className="max-w-2xl mx-auto mb-6">
            <div className="flex flex-col items-center gap-3">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full"
              />
              <p className="text-white/30 text-sm">
                Scanning Facebook Groups, Twitter, Telegram, Forums...
              </p>
              <div className="flex items-center gap-2">
                {['Facebook', 'Twitter', 'Forums', 'Telegram'].map((platform, i) => (
                  <motion.span
                    key={platform}
                    initial={{ opacity: 0.3 }}
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1.5, delay: i * 0.3, repeat: Infinity }}
                    className="text-white/20 text-[10px]"
                  >
                    {platform}
                  </motion.span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Search Results ────────────────────────── */}
        <AnimatePresence>
          {leads.length > 0 && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-8"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-white font-semibold text-lg flex items-center gap-2">
                  <Target className="w-5 h-5 text-emerald-400" />
                  {searched ? 'Buyer Results' : 'Recent Leads'}
                  <span className="text-white/30 text-sm font-normal">
                    ({leads.length})
                  </span>
                </h2>

                {leads.length > 4 && (
                  <button
                    onClick={() => navigate('/leads')}
                    className="text-emerald-400 text-xs hover:text-emerald-300 transition-colors"
                  >
                    View all →
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {leads.slice(0, 9).map((lead, index) => (
                  <motion.div
                    key={lead.id || lead.url || index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <LeadCard lead={lead} />
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Live Feed Section ─────────────────────── */}
        <div className="mt-8">
          <div className="flex items-center gap-2 mb-4">
            <Radio className={`w-5 h-5 ${isConnected ? 'text-red-400 animate-pulse' : 'text-white/20'}`} />
            <h2 className="text-white font-semibold text-lg">
              Real-Time Buyer Feed
            </h2>
            {isConnected && (
              <span className="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 
                               text-red-400 text-[10px] font-medium animate-pulse">
                LIVE
              </span>
            )}
            
            {/* Test Button */}
            <button 
              onClick={testNotification} 
              className="ml-auto px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400 rounded-xl text-xs transition-colors flex items-center gap-2"
            >
              🔔 Test HOT Notification
            </button>
          </div>
          <LiveBuyerFeed />
        </div>

      </div>
    </div>
  );
};

export default Dashboard;
