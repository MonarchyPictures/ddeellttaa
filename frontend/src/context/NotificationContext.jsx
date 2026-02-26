// frontend/src/context/NotificationContext.jsx
// ============================================================
// NOTIFICATION CONTEXT — Global notification state manager
// ============================================================
// Manages:
// - WebSocket connection to backend
// - Notification storage and unread counts
// - Sound alerts for hot leads
// - Toast notification queue
// ============================================================

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useCallback
} from 'react';
import getApiUrl from '../config';

const NotificationContext = createContext(null);

export const useNotifications = () => useContext(NotificationContext);

// Notification sound (base64 encoded short beep)
// You can replace this with any .mp3 URL
const NOTIFICATION_SOUND_URL = null; // Will use Web Audio API instead

const generateNotificationSound = () => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    // Pleasant notification tone
    oscillator.frequency.setValueAtTime(880, audioContext.currentTime); // A5
    oscillator.frequency.setValueAtTime(1108, audioContext.currentTime + 0.1); // C#6
    oscillator.frequency.setValueAtTime(1320, audioContext.currentTime + 0.2); // E6

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
  } catch (e) {
    // Audio not supported, silently fail
  }
};

const generateHotLeadSound = () => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();

    const playTone = (freq, startTime, duration) => {
      const osc = audioContext.createOscillator();
      const gain = audioContext.createGain();
      osc.connect(gain);
      gain.connect(audioContext.destination);
      osc.frequency.setValueAtTime(freq, startTime);
      gain.gain.setValueAtTime(0.3, startTime);
      gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
      osc.start(startTime);
      osc.stop(startTime + duration);
    };

    const now = audioContext.currentTime;
    // Ascending three-tone alert
    playTone(523, now, 0.15);        // C5
    playTone(659, now + 0.15, 0.15); // E5
    playTone(784, now + 0.3, 0.3);   // G5
  } catch (e) {
    // Audio not supported
  }
};

export const NotificationProvider = ({ children }) => {
  // ── State ──────────────────────────────────────
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [toasts, setToasts] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [leads, setLeads] = useState([]); // Kept for backward compatibility with LiveFeed

  // ── Refs ───────────────────────────────────────
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;
  
  // ── Settings ───────────────────────────────────
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [desktopNotifications, setDesktopNotifications] = useState(false);

  // Request desktop notification permission
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        setDesktopNotifications(permission === 'granted');
      });
    } else if ('Notification' in window && Notification.permission === 'granted') {
      setDesktopNotifications(true);
    }
  }, []);
  
  // ── Helpers ────────────────────────────────────
  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id && t.toastId !== id));
  }, []);

  const addToast = useCallback((message, type = 'info', data = {}) => {
    const id = Date.now();
    setToasts(prev => [...prev, { 
      id, 
      toastId: id, 
      message, 
      type, 
      ...data 
    }]);
    setTimeout(() => removeToast(id), 5000);
  }, [removeToast]);
  
  const dismissToast = removeToast;

  
  const markAsRead = useCallback((id) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: 1, read: true } : n))
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: 1, read: true })));
    setUnreadCount(0);
  }, []);
  
  const clearNotifications = useCallback(() => {
      setNotifications([]);
      setUnreadCount(0);
  }, []);

  // ── Message Handler ────────────────────────────
  const handleIncomingMessage = useCallback((data) => {
    if (data.type === 'new_buyer' || data.type === 'new_lead') {
      const lead = data.data;
      const badge = lead.badge || 'COLD';
      const isHot = badge === 'HOT';
      
      // Update leads list (LiveFeed compatibility)
      setLeads((prev) => {
        if (prev.some(l => l.id === lead.id)) return prev;
        return [lead, ...prev].slice(0, 50);
      });

      // 1. Add to notifications
      const notification = {
        id: lead.id || Date.now(),
        lead_id: lead.id,
        message: `${badge === 'HOT' ? '🔥 ' : ''}${lead.buyer_name} is looking for: ${lead.buyer_request_snippet?.substring(0, 60)}...`,
        type: badge === 'HOT' ? 'hot' : 'info',
        created_at: new Date().toISOString(),
        timestamp: new Date().toISOString(),
        is_read: 0,
        read: false,
        data: lead,
        lead: lead,
        badge
      };

      setNotifications((prev) => [notification, ...prev]);
      setUnreadCount((prev) => prev + 1);

      // 2. Play Sound
      if (soundEnabled) {
          if (badge === 'HOT' || badge === 'WARM') {
              generateHotLeadSound();
          } else {
              generateNotificationSound();
          }
      }

      // 3. Show Toast
      addToast(
        `New ${badge} Lead: ${lead.buyer_name}`, 
        badge === 'HOT' ? 'hot' : 'info', 
        { lead, badge }
      );
      
      // 4. Desktop Notification
      if (desktopNotifications && document.hidden) {
           new Notification(`New ${badge} Lead: ${lead.buyer_name}`, {
               body: lead.buyer_request_snippet || 'Check dashboard for details',
               icon: '/favicon.ico'
           });
      }
    }
  }, [soundEnabled, desktopNotifications, addToast]);

  // ── WebSocket Connection ───────────────────────
  const connectWebSocket = useCallback(() => {
    // Determine WebSocket URL
    const apiUrl = getApiUrl();
    let baseUrl;
    if (apiUrl.startsWith('http://') || apiUrl.startsWith('https://')) {
      baseUrl = apiUrl;
    } else if (import.meta.env.DEV) {
      baseUrl = `http://localhost:8001${apiUrl}`;
    } else {
      baseUrl = `${window.location.protocol}//${window.location.host}${apiUrl}`;
    }

    const wsUrl = baseUrl
      .replace('https://', 'wss://')
      .replace('http://', 'ws://')
      .replace(/\/$/, '') + '/telegram/ws';

    console.log('Connecting to WebSocket URL:', wsUrl);

    if (wsRef.current) {
        wsRef.current.close();
    }

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('🔴 WebSocket connected — Live notifications active');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleIncomingMessage(data);
        } catch (e) {
          console.error('WebSocket message parse error:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Auto-reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`Reconnecting in ${delay / 1000}s...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connectWebSocket();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

    } catch (e) {
      console.error('WebSocket connection failed:', e);
      setIsConnected(false);
    }
  }, [handleIncomingMessage]);

  // Connect on mount
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        // Prevent reconnect logic when unmounting or re-running effect
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connectWebSocket]);

  // ── Test Helper ────────────────────────────────
  const simulateNotification = useCallback((leadData) => {
    handleIncomingMessage({
      type: 'new_buyer',
      data: leadData
    });
  }, [handleIncomingMessage]);

  const value = {
    notifications,
    leads, // Export leads for LiveFeed
    unreadCount,
    toasts,
    isConnected,
    markAsRead,
    markAllAsRead,
    clearAll: clearNotifications,
    clearNotifications,
    removeToast,
    dismissToast,
    addToast,
    connectWebSocket,
    simulateNotification,
    setSoundEnabled,
    soundEnabled,
    desktopNotifications,
    setDesktopNotifications
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export default NotificationContext;
