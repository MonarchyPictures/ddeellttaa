// frontend/src/components/NotificationBell.jsx
// ============================================================
// NOTIFICATION BELL — Header component with dropdown
// ============================================================

import React, { useState, useRef, useEffect } from 'react';
import { Bell, BellRing, X, Check, CheckCheck, Volume2, VolumeX, Wifi, WifiOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNotifications } from '../context/NotificationContext';
import NotificationItem from './NotificationItem';

const NotificationBell = () => {
  const {
    notifications,
    unreadCount,
    isConnected,
    soundEnabled,
    markAllAsRead,
    clearAll,
    setSoundEnabled
  } = useNotifications();

  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const BellIcon = unreadCount > 0 ? BellRing : Bell;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl hover:bg-white/5 transition-colors"
      >
        <BellIcon
          className={`w-5 h-5 ${
            unreadCount > 0 ? 'text-amber-400 animate-pulse' : 'text-white/60'
          }`}
        />

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-1 -right-1 min-w-[18px] h-[18px] 
                       flex items-center justify-center
                       bg-red-500 text-white text-[10px] font-bold 
                       rounded-full px-1"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </motion.span>
        )}

        {/* Connection indicator */}
        <span
          className={`absolute bottom-0 right-0 w-2 h-2 rounded-full ${
            isConnected ? 'bg-green-400' : 'bg-red-400'
          }`}
        />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-2 w-96 max-h-[80vh] 
                       bg-[#0A0A0B] border border-white/10 rounded-2xl 
                       shadow-2xl shadow-black/50 overflow-hidden z-50"
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h3 className="text-white font-semibold text-sm">Notifications</h3>
                {unreadCount > 0 && (
                  <span className="bg-red-500/20 text-red-400 text-xs px-2 py-0.5 rounded-full">
                    {unreadCount} new
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1">
                {/* Connection Status */}
                <button
                  className="p-1.5 rounded-lg hover:bg-white/5"
                  title={isConnected ? 'Live connected' : 'Disconnected'}
                >
                  {isConnected ? (
                    <Wifi className="w-3.5 h-3.5 text-green-400" />
                  ) : (
                    <WifiOff className="w-3.5 h-3.5 text-red-400" />
                  )}
                </button>

                {/* Sound Toggle */}
                <button
                  onClick={() => setSoundEnabled(!soundEnabled)}
                  className="p-1.5 rounded-lg hover:bg-white/5"
                  title={soundEnabled ? 'Mute sounds' : 'Enable sounds'}
                >
                  {soundEnabled ? (
                    <Volume2 className="w-3.5 h-3.5 text-white/40" />
                  ) : (
                    <VolumeX className="w-3.5 h-3.5 text-white/20" />
                  )}
                </button>

                {/* Mark All Read */}
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="p-1.5 rounded-lg hover:bg-white/5"
                    title="Mark all as read"
                  >
                    <CheckCheck className="w-3.5 h-3.5 text-white/40" />
                  </button>
                )}
              </div>
            </div>

            {/* Live Status Bar */}
            <div className={`px-4 py-1.5 text-xs flex items-center gap-2 ${
              isConnected ? 'bg-green-500/5 text-green-400' : 'bg-red-500/5 text-red-400'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
              }`} />
              {isConnected ? 'Live — Monitoring Telegram groups' : 'Disconnected — Reconnecting...'}
            </div>

            {/* Notification List */}
            <div className="overflow-y-auto max-h-[60vh] divide-y divide-white/5">
              {notifications.length > 0 ? (
                notifications.slice(0, 20).map((notif) => (
                  <NotificationItem key={notif.id} notification={notif} />
                ))
              ) : (
                <div className="px-4 py-12 text-center">
                  <Bell className="w-8 h-8 text-white/10 mx-auto mb-3" />
                  <p className="text-white/30 text-sm">No notifications yet</p>
                  <p className="text-white/15 text-xs mt-1">
                    Buyer alerts will appear here in real-time
                  </p>
                </div>
              )}
            </div>

            {/* Footer */}
            {notifications.length > 0 && (
              <div className="px-4 py-2 border-t border-white/5 flex justify-between">
                <button
                  onClick={clearAll}
                  className="text-xs text-white/30 hover:text-white/60 transition-colors"
                >
                  Clear all
                </button>
                <span className="text-xs text-white/20">
                  {notifications.length} total
                </span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default NotificationBell;