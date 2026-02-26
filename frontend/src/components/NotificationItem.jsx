// frontend/src/components/NotificationItem.jsx
// ============================================================
// SINGLE NOTIFICATION ITEM — Rendered in the bell dropdown
// ============================================================

import React from 'react';
import { Phone, MessageCircle, ExternalLink, Send, Clock, MapPin } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNotifications } from '../context/NotificationContext';

const NotificationItem = ({ notification }) => {
  const { markAsRead } = useNotifications();
  const lead = notification.lead || {};
  const badge = notification.badge || 'COLD';
  const isRead = notification.read;

  const badgeConfig = {
    HOT: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', emoji: '🔥' },
    WARM: { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', emoji: '🟡' },
    COLD: { color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20', emoji: '🔵' }
  };
  const config = badgeConfig[badge] || badgeConfig.COLD;

  const phone = lead.phone || lead.contact_phone || '';
  const whatsappUrl = lead.whatsapp_url || lead.whatsapp_link || '';
  const telegramUser = lead.telegram_username || '';
  const url = lead.url || '';

  // Time ago
  const timeAgo = (timestamp) => {
    if (!timestamp) return '';
    const seconds = Math.floor((new Date() - new Date(timestamp)) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      onClick={() => markAsRead(notification.id)}
      className={`px-4 py-3 cursor-pointer transition-colors
        ${isRead ? 'bg-transparent' : `${config.bg}`}
        hover:bg-white/5`}
    >
      {/* Top Row: Badge + Title + Time */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-sm flex-shrink-0">{config.emoji}</span>
          <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${config.bg} ${config.color}`}>
            {badge}
          </span>
          <span className="text-white text-sm font-medium truncate">
            {lead.buyer_name || 'New Buyer'}
          </span>
        </div>
        <span className="text-white/20 text-[10px] flex-shrink-0 flex items-center gap-1">
          <Clock className="w-2.5 h-2.5" />
          {timeAgo(notification.timestamp)}
        </span>
      </div>

      {/* Message Preview */}
      <p className="text-white/50 text-xs leading-relaxed line-clamp-2 ml-6 mb-2">
        {lead.buyer_request_snippet || lead.title || notification.body || ''}
      </p>

      {/* Meta Row: Location + Source */}
      <div className="flex items-center gap-3 ml-6 mb-2">
        {lead.location && (
          <span className="text-white/25 text-[10px] flex items-center gap-1">
            <MapPin className="w-2.5 h-2.5" />
            {lead.location}
          </span>
        )}
        {lead.source && (
          <span className="text-white/25 text-[10px]">
            via {lead.source}
          </span>
        )}
        {lead.price && lead.price !== 'Contact for Price' && (
          <span className="text-green-400/60 text-[10px] font-medium">
            {lead.price}
          </span>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2 ml-6">
        {whatsappUrl && (
          <a
            href={whatsappUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 px-2 py-1 rounded-lg
                       bg-green-500/10 text-green-400 text-[10px] font-medium
                       hover:bg-green-500/20 transition-colors"
          >
            <MessageCircle className="w-3 h-3" />
            WhatsApp
          </a>
        )}

        {phone && (
          <a
            href={`tel:${phone}`}
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 px-2 py-1 rounded-lg
                       bg-blue-500/10 text-blue-400 text-[10px] font-medium
                       hover:bg-blue-500/20 transition-colors"
          >
            <Phone className="w-3 h-3" />
            Call
          </a>
        )}

        {telegramUser && (
          <a
            href={`https://t.me/${telegramUser}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 px-2 py-1 rounded-lg
                       bg-sky-500/10 text-sky-400 text-[10px] font-medium
                       hover:bg-sky-500/20 transition-colors"
          >
            <Send className="w-3 h-3" />
            Telegram
          </a>
        )}

        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 px-2 py-1 rounded-lg
                       bg-white/5 text-white/40 text-[10px]
                       hover:bg-white/10 transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            Source
          </a>
        )}
      </div>

      {/* Unread indicator */}
      {!isRead && (
        <div className="absolute left-1 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-blue-400" />
      )}
    </motion.div>
  );
};

export default NotificationItem;
