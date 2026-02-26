import React, { useState, useEffect } from 'react';
import { Activity, Zap, MessageCircle, TrendingUp } from 'lucide-react';
import getApiUrl, { getApiKey } from '../config';

const SuccessTicker = ({ onMetricClick }) => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const fetchStats = async (retries = 3) => {
      try {
        const apiUrl = getApiUrl();
        const apiKey = getApiKey();
        const res = await fetch(`${apiUrl}/success/stats`, {
          headers: { 
            'X-API-Key': apiKey,
            'Accept': 'application/json'
          }
        });
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        } else {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
      } catch (err) {
        if (retries > 0) {
          const delay = Math.pow(2, 3 - retries) * 1000;
          console.warn(`Failed to fetch success stats, retrying in ${delay}ms...`, err);
          setTimeout(() => fetchStats(retries - 1), delay);
        } else {
          console.error("Failed to fetch success stats after 3 retries:", err);
        }
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  if (!stats) return null;

  return (
    <div className="w-full bg-blue-600/10 border-y border-blue-500/20 py-2 px-4 flex flex-wrap md:flex-nowrap items-center justify-center gap-4 md:gap-8 overflow-hidden">
      <div className="flex items-center gap-2">
        <Activity size={14} className="text-blue-500 animate-pulse" />
        <span className="text-[10px] font-black text-white/60 uppercase tracking-widest">
          Market Pulse:
        </span>
      </div>
      
      <button 
        onClick={() => onMetricClick?.('/leads?type=active')}
        className="flex items-center gap-2 hover:bg-white/5 px-2 py-1 rounded transition-colors group"
      >
        <span className="text-lg group-hover:scale-110 transition-transform">🔥</span>
        <span className="text-[10px] font-black text-white uppercase tracking-widest">
          {stats.active_listings_24h} ACTIVE LISTINGS (24H)
        </span>
      </button>

      <button 
        onClick={() => onMetricClick?.('/leads?type=urgent')}
        className="flex items-center gap-2 hover:bg-white/5 px-2 py-1 rounded transition-colors group"
      >
        <span className="text-lg group-hover:scale-110 transition-transform">⚡</span>
        <span className="text-[10px] font-black text-white uppercase tracking-widest">
          {stats.urgent_sellers} URGENT BUYERS
        </span>
      </button>

      <button 
        onClick={() => onMetricClick?.('/leads?type=whatsapp')}
        className="flex items-center gap-2 hover:bg-white/5 px-2 py-1 rounded transition-colors group"
      >
        <span className="text-lg group-hover:scale-110 transition-transform">💬</span>
        <span className="text-[10px] font-black text-white uppercase tracking-widest">
          {stats.whatsapp_taps_today} WHATSAPP TAPS
        </span>
      </button>

      <button 
        onClick={() => onMetricClick?.('/leads?type=high_intent')}
        className="flex items-center gap-2 hover:bg-white/5 px-2 py-1 rounded transition-colors group"
      >
        <span className="text-lg group-hover:scale-110 transition-transform">🎯</span>
        <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest">
          {stats.high_intent_matches} MATCHES ABOVE 0.8
        </span>
      </button>
    </div>
  );
};

export default SuccessTicker;
