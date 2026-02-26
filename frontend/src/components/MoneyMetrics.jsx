import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import getApiUrl, { getApiKey } from '../config';

const MoneyMetrics = ({ onMetricClick }) => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    active_listings_24h: 0,
    urgent_sellers: 0,
    whatsapp_taps_today: 0,
    high_intent_matches: 0
  });

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
          console.warn(`Failed to fetch money metrics, retrying in ${delay}ms...`, err);
          setTimeout(() => fetchStats(retries - 1), delay);
        } else {
          console.error("Failed to fetch money metrics after 3 retries:", err);
        }
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Every 30s for freshness
    return () => clearInterval(interval);
  }, []);

  const metrics = [
    { 
      label: 'ACTIVE LEADS (24H)', 
      value: stats.active_listings_24h, 
      icon: '🔥', 
      color: 'text-orange-500', 
      bg: 'bg-orange-500/5',
      filter: '/leads?type=active'
    },
    { 
      label: 'HIGH INTENT', 
      value: stats.high_intent_matches, 
      icon: '🎯', 
      color: 'text-blue-500', 
      bg: 'bg-blue-500/5',
      filter: '/leads?type=high_intent'
    },
    { 
      label: 'WHATSAPP TAPS', 
      value: stats.whatsapp_taps_today, 
      icon: '💬', 
      color: 'text-green-500', 
      bg: 'bg-green-500/5',
      filter: '/leads?type=whatsapp'
    }
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
      {metrics.map((m, i) => (
        <motion.div
          key={m.label}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => {
            if (onMetricClick) {
              onMetricClick(m.filter);
            } else {
              navigate(m.filter);
            }
          }}
          className={`${m.bg} border border-white/5 p-5 rounded-3xl flex flex-col items-start relative overflow-hidden group hover:border-blue-500/50 hover:bg-blue-500/20 cursor-pointer transition-all active:scale-95 shadow-lg hover:shadow-blue-500/20`}
          title="Click to view active leads from last 24h"
        >
          <div className="flex items-center justify-between w-full mb-2">
            <span className="text-2xl">{m.icon}</span>
            <div className={`h-1.5 w-1.5 rounded-full ${m.color.replace('text', 'bg')} animate-pulse`}></div>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-xl md:text-3xl font-black text-white mb-1 tabular-nums">{m.value}</span>
          </div>
          <span className="text-[9px] font-black text-white/30 uppercase tracking-[0.2em] leading-tight group-hover:text-white/60 transition-colors">
            {m.label}
          </span>
          <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <span className="text-6xl grayscale">{m.icon}</span>
          </div>
        </motion.div>
      ))}
    </div>
  );
};

export default MoneyMetrics;
