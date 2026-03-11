import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Radio, Phone, ExternalLink, MapPin, Clock, Zap, Flame, TrendingUp } from 'lucide-react';

/**
 * LIVE BUYERS TICKER - Apollo.io/Clay style magical real-time feed
 * Creates urgency and excitement with animated entries
 */
const LiveBuyersTicker = ({ leads = [], maxItems = 50 }) => {
  const [feed, setFeed] = useState(leads.slice(0, maxItems));
  const [isLive, setIsLive] = useState(true);
  const [stats, setStats] = useState({ total: 0, hot: 0, today: 0 });
  const feedEndRef = useRef(null);
  
  // Auto-scroll to newest
  useEffect(() => {
    if (isLive && feedEndRef.current) {
      feedEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [feed, isLive]);

  // Update stats
  useEffect(() => {
    const hot = feed.filter(l => (l.ai_intent_score || l.intent_score || 0) >= 75).length;
    const today = feed.filter(l => {
      const date = new Date(l.timestamp || l.created_at);
      return date > new Date(Date.now() - 24 * 60 * 60 * 1000);
    }).length;
    setStats({ total: feed.length, hot, today });
  }, [feed]);

  // Simulate real-time updates (replace with actual WebSocket)
  useEffect(() => {
    if (leads.length > feed.length) {
      // New leads arrived
      const newLeads = leads.slice(0, leads.length - feed.length);
      setFeed(prev => [...newLeads, ...prev].slice(0, maxItems));
    }
  }, [leads]);

  const getSourceIcon = (source) => {
    const icons = {
      telegram: '✈️',
      facebook: '📘',
      jiji: '🛒',
      reddit: '🔴',
      google: '🔍',
      twitter: '🐦',
      whatsapp: '💬'
    };
    return icons[source?.toLowerCase()] || '📡';
  };

  const getTimeAgo = (timestamp) => {
    if (!timestamp) return 'now';
    const seconds = Math.floor((Date.now() - new Date(timestamp)) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const getScoreColor = (score) => {
    if (score >= 75) return 'text-red-400 bg-red-500/10 border-red-500/30';
    if (score >= 50) return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
  };

  return (
    <div className="bg-[#0A0A0B] rounded-2xl border border-white/5 overflow-hidden">
      {/* Header - Apollo.io Style */}
      <div className="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-gray-900 to-black">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Live Indicator */}
            <div className="relative">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
              <div className="absolute inset-0 w-3 h-3 bg-green-500 rounded-full animate-ping opacity-75" />
            </div>
            
            <div>
              <h2 className="text-lg font-black text-white flex items-center gap-2">
                LIVE BUYERS
                <span className="text-[10px] font-bold px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full border border-green-500/30">
                  REAL-TIME
                </span>
              </h2>
              <p className="text-white/40 text-xs">
                Fresh buyer signals from across the web
              </p>
            </div>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-2xl font-black text-white">{stats.total}</div>
              <div className="text-[10px] text-white/30 uppercase tracking-wider">Total</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-black text-red-400">{stats.hot}</div>
              <div className="text-[10px] text-white/30 uppercase tracking-wider">Hot</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-black text-green-400">{stats.today}</div>
              <div className="text-[10px] text-white/30 uppercase tracking-wider">Today</div>
            </div>
          </div>
        </div>
      </div>

      {/* Ticker Feed */}
      <div className="relative max-h-[600px] overflow-y-auto">
        {/* Gradient Overlay for Depth */}
        <div className="sticky top-0 h-8 bg-gradient-to-b from-[#0A0A0B] to-transparent z-10 pointer-events-none" />
        
        <div className="divide-y divide-white/5">
          <AnimatePresence initial={false}>
            {feed.map((lead, index) => {
              const score = lead.ai_intent_score || lead.intent_score || 0;
              const isHot = score >= 75;
              const isNew = index < 3;
              
              return (
                <motion.div
                  key={lead.id || index}
                  initial={{ opacity: 0, x: -30, scale: 0.95 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ 
                    duration: 0.4, 
                    delay: index * 0.05,
                    type: "spring",
                    stiffness: 100
                  }}
                  className={`
                    group relative px-6 py-4 hover:bg-white/[0.02] transition-colors cursor-pointer
                    ${isNew ? 'bg-white/[0.01]' : ''}
                  `}
                >
                  {/* New Indicator */}
                  {isNew && (
                    <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gradient-to-b from-green-500 to-transparent" />
                  )}

                  <div className="flex items-start gap-4">
                    {/* Time Badge */}
                    <div className="flex-shrink-0 w-20">
                      <div className={`
                        flex items-center gap-1.5 text-xs font-bold
                        ${isNew ? 'text-green-400' : 'text-white/30'}
                      `}>
                        <div className={`
                          w-2 h-2 rounded-full
                          ${isNew ? 'bg-green-500 animate-pulse' : 'bg-white/20'}
                        `} />
                        {getTimeAgo(lead.timestamp || lead.created_at)}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {/* Buyer Request */}
                      <p className="text-white font-medium text-sm truncate group-hover:text-blue-400 transition-colors">
                        {lead.text || lead.buyer_request_snippet || lead.title || 'Looking for product'}
                      </p>
                      
                      {/* Meta Row */}
                      <div className="flex items-center gap-4 mt-1.5">
                        {/* Source */}
                        <span className="flex items-center gap-1.5 text-xs text-white/40">
                          <span>{getSourceIcon(lead.source)}</span>
                          {lead.source || 'Web'}
                        </span>
                        
                        {/* Location */}
                        {lead.location && (
                          <span className="flex items-center gap-1 text-xs text-white/40">
                            <MapPin size={10} />
                            {lead.location}
                          </span>
                        )}
                        
                        {/* Phone Indicator */}
                        {(lead.phone || lead.contact_phone) && (
                          <span className="flex items-center gap-1 text-xs text-green-400">
                            <Phone size={10} />
                            Has Phone
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Score Badge */}
                    <div className="flex-shrink-0">
                      <div className={`
                        flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-black
                        ${getScoreColor(score)}
                      `}>
                        {isHot && <Flame size={12} />}
                        {score}
                      </div>
                    </div>

                    {/* Action */}
                    <a
                      href={lead.url || lead.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <ExternalLink size={16} className="text-white/40 hover:text-white" />
                    </a>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
        
        <div ref={feedEndRef} />
        
        {/* Bottom Gradient */}
        <div className="sticky bottom-0 h-12 bg-gradient-to-t from-[#0A0A0B] to-transparent pointer-events-none" />
      </div>

      {/* Footer Controls */}
      <div className="px-6 py-3 border-t border-white/5 bg-black/20 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-white/30">
          <span className="flex items-center gap-1.5">
            <Activity size={12} className="text-green-500" />
            Monitoring {feed.length} sources
          </span>
          <span>•</span>
          <span>Updated every 30s</span>
        </div>
        
        <button
          onClick={() => setIsLive(!isLive)}
          className={`
            flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all
            ${isLive 
              ? 'bg-green-500/10 text-green-400 border border-green-500/30' 
              : 'bg-white/5 text-white/40 border border-white/10'
            }
          `}
        >
          <Radio size={12} />
          {isLive ? 'LIVE' : 'PAUSED'}
        </button>
      </div>
    </div>
  );
};

export default LiveBuyersTicker;
