// frontend/src/components/LiveBuyerFeed.jsx
// ============================================================
// LIVE BUYER FEED — Real-time stream of buyer signals
// ============================================================

import React, { useState, useRef, useEffect } from 'react';
import { Activity, Zap, Filter, Pause, Play, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNotifications } from '../context/NotificationContext';

const LiveBuyerFeed = ({ leads: propLeads }) => {
  const { leads: contextLeads, isConnected } = useNotifications();
  const liveFeed = propLeads || contextLeads;
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState('all'); // all, hot, warm
  const [expandedId, setExpandedId] = useState(null);
  const feedRef = useRef(null);

  // Auto-scroll to top when new items arrive (unless paused)
  useEffect(() => {
    if (!isPaused && feedRef.current) {
      feedRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [liveFeed.length, isPaused]);

  // Filter leads
  const filteredFeed = liveFeed.filter(lead => {
    if (filter === 'all') return true;
    if (filter === 'hot') return lead.badge === 'HOT';
    if (filter === 'warm') return lead.badge === 'HOT' || lead.badge === 'WARM';
    if (filter === 'with_phone') return lead.phone || lead.contact_phone;
    return true;
  });

  const hotCount = liveFeed.filter(l => l.badge === 'HOT').length;
  const warmCount = liveFeed.filter(l => l.badge === 'WARM').length;
  const withPhoneCount = liveFeed.filter(l => l.phone || l.contact_phone).length;

  return (
    <div className="bg-[#0A0A0B] border border-white/5 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Activity className={`w-5 h-5 ${isConnected ? 'text-green-400' : 'text-red-400'}`} />
              {isConnected && (
                <motion.span
                  animate={{ scale: [1, 1.5, 1], opacity: [1, 0, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-green-400 rounded-full"
                />
              )}
            </div>
            <div>
              <h3 className="text-white font-semibold text-sm">Live Buyer Feed</h3>
              <p className="text-white/30 text-[10px]">
                {isConnected ? 'Monitoring Telegram groups in real-time' : 'Disconnected'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Pause/Play */}
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`p-1.5 rounded-lg transition-colors ${
                isPaused ? 'bg-amber-500/10 text-amber-400' : 'bg-white/5 text-white/40'
              }`}
              title={isPaused ? 'Resume auto-scroll' : 'Pause auto-scroll'}
            >
              {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            </button>

            {/* Stats */}
            <span className="text-white/20 text-xs">
              {liveFeed.length} signals
            </span>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 flex-wrap">
          {[
            { key: 'all', label: 'All', count: liveFeed.length },
            { key: 'hot', label: '🔥 Hot', count: hotCount },
            { key: 'warm', label: '🟡 Warm+', count: warmCount + hotCount },
            { key: 'with_phone', label: '📞 With Phone', count: withPhoneCount },
          ].map(({ key, label, count }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-1 rounded-full text-[10px] font-medium transition-colors ${
                filter === key
                  ? 'bg-white/10 text-white'
                  : 'bg-white/3 text-white/30 hover:bg-white/5 hover:text-white/50'
              }`}
            >
              {label} ({count})
            </button>
          ))}
        </div>
      </div>

      {/* Feed */}
      <div
        ref={feedRef}
        className="overflow-y-auto max-h-[600px] divide-y divide-white/5"
      >
        <AnimatePresence mode="popLayout">
          {filteredFeed.length > 0 ? (
            filteredFeed.map((lead, index) => (
              <motion.div
                key={lead.id || index}
                layout
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
              >
                <LiveFeedItem
                  lead={lead}
                  isNew={index === 0}
                  expanded={expandedId === (lead.id || index)}
                  onToggle={() => setExpandedId(
                    expandedId === (lead.id || index) ? null : (lead.id || index)
                  )}
                />
              </motion.div>
            ))
          ) : (
            <div className="px-5 py-16 text-center">
              <Zap className="w-8 h-8 text-white/10 mx-auto mb-3" />
              <p className="text-white/30 text-sm">Waiting for buyer signals...</p>
              <p className="text-white/15 text-xs mt-1">
                {isConnected
                  ? 'Monitoring active — new buyers will appear here instantly'
                  : 'Connect to start receiving real-time buyer alerts'}
              </p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

// ── Individual Feed Item ─────────────────────────────────
const LiveFeedItem = ({ lead, isNew, expanded, onToggle }) => {
  const badge = lead.badge || 'COLD';
  const phone = lead.phone || lead.contact_phone || '';
  const whatsappUrl = lead.whatsapp_url || lead.whatsapp_link || '';
  const telegramUser = lead.telegram_username || '';

  const badgeColor = {
    HOT: 'bg-red-500/10 text-red-400 border-red-500/20',
    WARM: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    COLD: 'bg-blue-500/10 text-blue-400 border-blue-500/20'
  };

  const timeAgo = (timestamp) => {
    if (!timestamp) return '';
    const seconds = Math.floor((new Date() - new Date(timestamp)) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  };

  return (
    <div
      className={`px-5 py-3 cursor-pointer transition-colors hover:bg-white/3
        ${isNew ? 'bg-white/[0.02]' : ''}`}
      onClick={onToggle}
    >
      {/* Main Row */}
      <div className="flex items-start gap-3">
        {/* Badge */}
        <span className={`mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold border
          ${badgeColor[badge] || badgeColor.COLD}`}>
          {badge}
        </span>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-white text-sm font-medium truncate">
              {lead.buyer_name || 'Unknown Buyer'}
            </p>
            <span className="text-white/20 text-[10px] flex-shrink-0">
              {timeAgo(lead.created_at || lead.posted_at)}
            </span>
          </div>

          <p className="text-white/40 text-xs line-clamp-2 mt-0.5">
            {lead.buyer_request_snippet || lead.title || ''}
          </p>

          <div className="flex items-center gap-3 mt-1.5">
            {lead.location && (
              <span className="text-white/20 text-[10px]">📍 {lead.location}</span>
            )}
            {lead.price && lead.price !== 'Contact for Price' && (
              <span className="text-green-400/50 text-[10px]">💰 {lead.price}</span>
            )}
            <span className="text-white/15 text-[10px]">
              via {lead.source || 'Telegram'}
            </span>
          </div>
        </div>

        <ChevronDown className={`w-4 h-4 text-white/20 transition-transform flex-shrink-0
          ${expanded ? 'rotate-180' : ''}`} />
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-3 ml-12 flex items-center gap-2 flex-wrap">
              {whatsappUrl && (
                <a
                  href={whatsappUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl
                             bg-green-500 text-white text-xs font-semibold
                             hover:bg-green-400 transition-colors"
                >
                  💬 WhatsApp
                </a>
              )}

              {phone && (
                <a
                  href={`tel:${phone}`}
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl
                             bg-blue-500/20 text-blue-400 text-xs font-medium
                             hover:bg-blue-500/30 transition-colors"
                >
                  📞 {phone}
                </a>
              )}

              {telegramUser && (
                <a
                  href={`https://t.me/${telegramUser}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl
                             bg-sky-500/20 text-sky-400 text-xs font-medium
                             hover:bg-sky-500/30 transition-colors"
                >
                  ✈️ @{telegramUser}
                </a>
              )}

              {lead.url && (
                <a
                  href={lead.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl
                             bg-white/5 text-white/40 text-xs
                             hover:bg-white/10 transition-colors"
                >
                  🔗 View Source
                </a>
              )}

              {/* Intent Score Bar */}
              <div className="flex items-center gap-2 ml-auto">
                <span className="text-white/20 text-[10px]">Intent</span>
                <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      (lead.intent_score || 0) > 0.7 ? 'bg-green-400' :
                      (lead.intent_score || 0) > 0.4 ? 'bg-amber-400' : 'bg-white/20'
                    }`}
                    style={{ width: `${(lead.intent_score || 0.5) * 100}%` }}
                  />
                </div>
                <span className="text-white/30 text-[10px]">
                  {((lead.intent_score || 0.5) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default LiveBuyerFeed;