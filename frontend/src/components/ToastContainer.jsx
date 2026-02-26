// frontend/src/components/ToastContainer.jsx
// ============================================================
// TOAST NOTIFICATIONS — Slide-in alerts for new buyers
// ============================================================

import React from 'react';
import { X, Phone, MessageCircle, Send, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNotifications } from '../context/NotificationContext';

const ToastContainer = () => {
  const { toasts, dismissToast } = useNotifications();

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-3 pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <Toast key={toast.toastId} toast={toast} onDismiss={dismissToast} />
        ))}
      </AnimatePresence>
    </div>
  );
};

const Toast = ({ toast, onDismiss }) => {
  const lead = toast.lead || {};
  const badge = toast.badge || 'WARM';

  const badgeStyles = {
    HOT: {
      gradient: 'from-red-500/20 to-orange-500/10',
      border: 'border-red-500/30',
      glow: 'shadow-red-500/20',
      accent: 'text-red-400',
      emoji: '🔥'
    },
    WARM: {
      gradient: 'from-amber-500/20 to-yellow-500/10',
      border: 'border-amber-500/30',
      glow: 'shadow-amber-500/20',
      accent: 'text-amber-400',
      emoji: '🟡'
    },
    COLD: {
      gradient: 'from-blue-500/20 to-cyan-500/10',
      border: 'border-blue-500/30',
      glow: 'shadow-blue-500/20',
      accent: 'text-blue-400',
      emoji: '🔵'
    }
  };

  const style = badgeStyles[badge] || badgeStyles.WARM;
  const phone = lead.phone || lead.contact_phone || '';
  const whatsappUrl = lead.whatsapp_url || lead.whatsapp_link || '';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 100, scale: 0.8 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.8 }}
      transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      className={`pointer-events-auto w-80 rounded-2xl border ${style.border}
                  bg-gradient-to-br ${style.gradient} bg-[#0A0A0B]
                  shadow-xl ${style.glow} backdrop-blur-xl
                  overflow-hidden`}
    >
      {/* Progress bar */}
      <motion.div
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: badge === 'HOT' ? 12 : 8, ease: 'linear' }}
        className={`h-0.5 ${
          badge === 'HOT' ? 'bg-red-500' : badge === 'WARM' ? 'bg-amber-500' : 'bg-blue-500'
        }`}
      />

      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">{style.emoji}</span>
            <div>
              <p className="text-white text-sm font-semibold">
                {badge === 'HOT' ? 'HOT BUYER ALERT' : 'New Buyer Found'}
              </p>
              <p className="text-white/40 text-[10px]">
                {lead.source || 'Telegram'} • just now
              </p>
            </div>
          </div>
          <button
            onClick={() => onDismiss(toast.toastId)}
            className="p-1 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-3.5 h-3.5 text-white/30" />
          </button>
        </div>

        {/* Buyer Info */}
        <div className="mb-3">
          <p className={`text-sm font-medium ${style.accent}`}>
            {lead.buyer_name || 'Unknown Buyer'}
          </p>
          <p className="text-white/50 text-xs line-clamp-2 mt-1">
            {lead.buyer_request_snippet || lead.title || ''}
          </p>
          {lead.price && lead.price !== 'Contact for Price' && (
            <p className="text-green-400 text-xs font-medium mt-1">
              💰 Budget: {lead.price}
            </p>
          )}
          {lead.location && (
            <p className="text-white/30 text-[10px] mt-1">
              📍 {lead.location}
            </p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {whatsappUrl && (
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-1.5
                         px-3 py-2 rounded-xl
                         bg-green-500 text-white text-xs font-semibold
                         hover:bg-green-400 transition-colors"
            >
              <MessageCircle className="w-3.5 h-3.5" />
              WhatsApp Now
            </a>
          )}

          {phone && !whatsappUrl && (
            <a
              href={`tel:${phone}`}
              className="flex-1 flex items-center justify-center gap-1.5
                         px-3 py-2 rounded-xl
                         bg-blue-500 text-white text-xs font-semibold
                         hover:bg-blue-400 transition-colors"
            >
              <Phone className="w-3.5 h-3.5" />
              Call Now
            </a>
          )}

          {lead.url && (
            <a
              href={lead.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-1
                         px-3 py-2 rounded-xl
                         bg-white/5 text-white/60 text-xs
                         hover:bg-white/10 transition-colors"
            >
              <ArrowRight className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default ToastContainer;
