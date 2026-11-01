import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api/client';

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);
  const [counts, setCounts] = useState({
    unread_count: 0,
    stockout_count: 0,
    wastage_count: 0,
    festival_count: 0,
    restocked_count: 0,
    route_count: 0,
    total: 0,
  });
  const [loading, setLoading] = useState(false);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(() => {
    try {
      return localStorage.getItem('astrachain_sound_alerts') !== 'false';
    } catch {
      return true;
    }
  });
  const [liveToasts, setLiveToasts] = useState([]);
  const [nativePermission, setNativePermission] = useState(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      return Notification.permission;
    }
    return 'default';
  });

  const requestNativeNotificationPermission = async () => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      try {
        const perm = await Notification.requestPermission();
        setNativePermission(perm);
        return perm;
      } catch (err) {
        console.warn('Could not request notification permission:', err);
      }
    }
    return 'unsupported';
  };

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const audioCtxRef = useRef(null);

  // Toggle sound alert
  const toggleSound = () => {
    setSoundEnabled((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('astrachain_sound_alerts', String(next));
      } catch (e) {
        console.warn('Could not persist sound setting:', e);
      }
      return next;
    });
  };

  // Synthesized Web Audio Chime (no external audio files required)
  const playChime = useCallback((type = 'alert') => {
    if (!soundEnabled) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioCtx();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      const now = ctx.currentTime;
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gainNode = ctx.createGain();

      osc1.connect(gainNode);
      osc2.connect(gainNode);
      gainNode.connect(ctx.destination);

      if (type === 'success' || type === 'restock') {
        // High, bright, pleasant double-chime (C5 -> E5 -> G5)
        osc1.type = 'sine';
        osc2.type = 'sine';
        osc1.frequency.setValueAtTime(523.25, now); // C5
        osc1.frequency.exponentialRampToValueAtTime(659.25, now + 0.12); // E5
        osc2.frequency.setValueAtTime(659.25, now);
        osc2.frequency.exponentialRampToValueAtTime(783.99, now + 0.12); // G5

        gainNode.gain.setValueAtTime(0.001, now);
        gainNode.gain.linearRampToValueAtTime(0.18, now + 0.03);
        gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.45);

        osc1.start(now);
        osc2.start(now);
        osc1.stop(now + 0.46);
        osc2.stop(now + 0.46);
      } else if (type === 'festival') {
        // Festive triple shimmer chime
        osc1.type = 'triangle';
        osc2.type = 'sine';
        osc1.frequency.setValueAtTime(440, now); // A4
        osc1.frequency.exponentialRampToValueAtTime(880, now + 0.15); // A5
        osc2.frequency.setValueAtTime(659.25, now); // E5
        osc2.frequency.exponentialRampToValueAtTime(1108.73, now + 0.15); // C#6

        gainNode.gain.setValueAtTime(0.001, now);
        gainNode.gain.linearRampToValueAtTime(0.2, now + 0.04);
        gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.55);

        osc1.start(now);
        osc2.start(now);
        osc1.stop(now + 0.56);
        osc2.stop(now + 0.56);
      } else {
        // Attention alert chime for Stockout / Wastage (F#5 -> C#6 crisp ping)
        osc1.type = 'sine';
        osc2.type = 'triangle';
        osc1.frequency.setValueAtTime(739.99, now); // F#5
        osc1.frequency.exponentialRampToValueAtTime(1108.73, now + 0.08); // C#6
        osc2.frequency.setValueAtTime(369.99, now); // F#4

        gainNode.gain.setValueAtTime(0.001, now);
        gainNode.gain.linearRampToValueAtTime(0.22, now + 0.02);
        gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

        osc1.start(now);
        osc2.start(now);
        osc1.stop(now + 0.42);
        osc2.stop(now + 0.42);
      }
    } catch (e) {
      console.warn('Audio chime playback omitted:', e);
    }
  }, [soundEnabled]);

  // Add a live toast (strictly 1 notification block shown on screen)
  const addToast = useCallback((toast) => {
    const id = toast.id || `toast-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const newToast = {
      ...toast,
      id,
      createdAt: Date.now(),
      duration: toast.duration || 6500,
    };

    setLiveToasts([newToast]); // Display strictly only ONE block at any time
  }, []);

  const dismissToast = useCallback((id) => {
    setLiveToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Fetch full notification feed
  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getNotifications();
      if (res && res.data) {
        setNotifications(res.data);
        setCounts({
          unread_count: res.unread_count || 0,
          stockout_count: res.stockout_count || 0,
          wastage_count: res.wastage_count || 0,
          festival_count: res.festival_count || 0,
          restocked_count: res.restocked_count || 0,
          route_count: res.route_count || 0,
          total: res.total || res.data.length,
        });
      }
    } catch (err) {
      console.error('Error fetching notifications:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Process live notification incoming from WebSocket
  const handleLiveEvent = useCallback((eventData) => {
    const { event, notification } = eventData;
    if (!notification) return;

    // 1. Play auditory chime
    if (event === 'RESTOCK_COMPLETED' || event === 'FESTIVAL_PRESTOCKED' || event === 'WASTAGE_MITIGATED' || event === 'ROUTE_ARRIVAL') {
      playChime('success');
    } else if (event === 'FESTIVAL_ALERT') {
      playChime('festival');
    } else {
      playChime('alert');
    }

    // 2. Add to active live toast banners
    addToast(notification);

    // 2b. Native Mobile / Desktop Push Notification
    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
      try {
        new Notification(notification.title || 'AstraChain Alert', {
          body: notification.message || '',
          icon: '/vite.svg',
          badge: '/vite.svg',
          tag: notification.id,
        });
      } catch (e) {
        console.warn('Native notification omitted:', e);
      }
    }

    // 3. Prepend / update in local notifications list
    setNotifications((prev) => {
      const existsIndex = prev.findIndex((n) => n.id === notification.id);
      if (existsIndex >= 0) {
        const updated = [...prev];
        updated[existsIndex] = { ...updated[existsIndex], ...notification };
        return updated;
      }

      // 4. Update badge counts when new item arrives
      setCounts((prevCounts) => {
        const isUnread = !notification.is_read;
        const type = notification.type;
        return {
          ...prevCounts,
          unread_count: isUnread ? prevCounts.unread_count + 1 : prevCounts.unread_count,
          stockout_count: type === 'STOCKOUT' ? prevCounts.stockout_count + 1 : prevCounts.stockout_count,
          wastage_count: type === 'WASTAGE' ? prevCounts.wastage_count + 1 : prevCounts.wastage_count,
          festival_count: type === 'FESTIVAL' ? prevCounts.festival_count + 1 : prevCounts.festival_count,
          restocked_count: type === 'RESTOCKED' ? prevCounts.restocked_count + 1 : prevCounts.restocked_count,
          route_count: (type === 'ROUTE_ARRIVAL' || type === 'ROUTE') ? prevCounts.route_count + 1 : prevCounts.route_count,
          total: prevCounts.total + 1,
        };
      });

      return [notification, ...prev];
    });
  }, [playChime, addToast]);

  // WebSocket Connection Lifecycle
  useEffect(() => {
    let ws = null;
    let heartbeatInterval = null;

    const connectWs = () => {
      try {
        const wsUrl = api.getNotificationWsUrl();
        ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsWsConnected(true);
          // Start heartbeat ping every 25s
          heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send('ping');
            }
          }, 25000);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === 'CONNECTED' || data.event === 'PONG') {
              return;
            }
            handleLiveEvent(data);
          } catch (err) {
            console.warn('Non-JSON WebSocket message received:', event.data);
          }
        };

        ws.onclose = () => {
          setIsWsConnected(false);
          clearInterval(heartbeatInterval);
          // Attempt reconnection after 3 seconds
          reconnectTimeoutRef.current = setTimeout(connectWs, 3000);
        };

        ws.onerror = (err) => {
          console.warn('Live WebSocket notification warning (will retry):', err);
          ws?.close();
        };
      } catch (err) {
        console.warn('Could not establish WebSocket connection:', err);
        reconnectTimeoutRef.current = setTimeout(connectWs, 4000);
      }
    };

    connectWs();
    fetchNotifications();

    // Fallback sync polling every 20 seconds
    const pollInterval = setInterval(fetchNotifications, 20000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(heartbeatInterval);
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [fetchNotifications, handleLiveEvent]);

  // =========================================================================
  // Manager Actions
  // =========================================================================

  // 1-Click Restock
  const handleRestock = async (item) => {
    if (!item?.product_id) return null;
    const qty = item.suggested_qty || item.suggested_reorder_qty || 500;
    try {
      const res = await api.restockProduct({
        product_id: item.product_id,
        quantity: qty,
        notification_id: item.id,
      });

      if (res && res.success) {
        const liveNotif = res.notification || {
          id: `restock-${Date.now()}`,
          title: `Restocked: ${res.product_name || item.product_name || item.product_id}`,
          message: `Manager Daksh Mehta replenished +${qty.toLocaleString()} units. Warehouse balance updated to ${(res.new_stock || (item.current_stock || 0) + qty).toLocaleString()} units. Status: Optimal Stock.`,
          type: 'RESTOCKED',
          severity: 'SUCCESS',
          product_id: item.product_id,
          product_name: res.product_name || item.product_name || item.product_id,
          quantity_added: qty,
          new_stock: res.new_stock,
          timestamp: 'Just now',
          badge: 'Restocked',
          is_read: false,
          is_restocked: true,
        };

        // 1. Immediately pop up live floating toast on screen
        addToast(liveNotif);

        // 2. Prepend live notification to notifications list and update existing stockout
        setNotifications((prev) => {
          const updated = prev.map((n) =>
            n.product_id === item.product_id || n.id === item.id
              ? { ...n, is_restocked: true, can_restock: false, is_read: true, badge: 'Restocked' }
              : n
          );
          if (!updated.some((n) => n.id === liveNotif.id)) {
            return [liveNotif, ...updated];
          }
          return updated;
        });

        // 3. Make Notification Button live: increment unread_count and restocked_count
        setCounts((prev) => ({
          ...prev,
          stockout_count: Math.max(0, prev.stockout_count - 1),
          restocked_count: prev.restocked_count + 1,
          unread_count: prev.unread_count + 1,
          total: prev.total + 1,
        }));

        playChime('success');
        return res;
      }
    } catch (err) {
      console.error('Restock action failed:', err);
    }
    return null;
  };

  // 1-Click Dynamic Promo Markdown (Wastage Mitigation)
  const handleMitigateWastage = async (item, discountOverride = null) => {
    if (!item?.product_id) return null;
    const discount = discountOverride || item.discount_recommended || '30% Dynamic Markdown';
    try {
      const res = await api.mitigateWastage({
        product_id: item.product_id,
        discount,
        notification_id: item.id,
      });

      if (res && res.success) {
        const liveNotif = res.notification || {
          id: `wastage-mitigated-${Date.now()}`,
          title: `Markdown Active: ${res.product_name || item.product_name || item.product_id}`,
          message: `Dynamic promo discount (${discount}) is now active. Stock flagged for priority retail liquidation.`,
          type: 'WASTAGE',
          severity: 'SUCCESS',
          product_id: item.product_id,
          product_name: res.product_name || item.product_name || item.product_id,
          discount_applied: discount,
          timestamp: 'Just now',
          badge: 'Markdown Active',
          is_read: false,
          is_mitigated: true,
        };

        // 1. Pop up live floating toast
        addToast(liveNotif);

        // 2. Prepend live notification to notifications list
        setNotifications((prev) => {
          const updated = prev.map((n) =>
            n.product_id === item.product_id || n.id === item.id
              ? { ...n, is_mitigated: true, can_mitigate: false, is_read: true, badge: 'Markdown Active' }
              : n
          );
          if (!updated.some((n) => n.id === liveNotif.id)) {
            return [liveNotif, ...updated];
          }
          return updated;
        });

        // 3. Make Notification Button live
        setCounts((prev) => ({
          ...prev,
          wastage_count: Math.max(0, prev.wastage_count - 1),
          unread_count: prev.unread_count + 1,
          total: prev.total + 1,
        }));

        playChime('success');
        return res;
      }
    } catch (err) {
      console.error('Wastage mitigation action failed:', err);
    }
    return null;
  };

  // 1-Click Festival Surge Pre-Stock
  const handlePrestockFestival = async (item) => {
    if (!item?.product_id) return null;
    const qty = item.suggested_qty || item.extra_units_needed || 600;
    const festName = item.festival_name || 'Diwali';
    try {
      const res = await api.prestockFestival({
        product_id: item.product_id,
        festival_name: festName,
        quantity: qty,
        notification_id: item.id,
      });

      if (res && res.success) {
        const liveNotif = res.notification || {
          id: `fest-prestocked-${Date.now()}`,
          title: `Buffer Stocked: ${res.product_name || item.product_name || item.product_id}`,
          message: `+${qty.toLocaleString()} units safety stock allocated for ${festName} demand surge. Fulfillment ready.`,
          type: 'FESTIVAL',
          severity: 'SUCCESS',
          product_id: item.product_id,
          product_name: res.product_name || item.product_name || item.product_id,
          festival_name: festName,
          quantity_added: qty,
          timestamp: 'Just now',
          badge: 'Buffer Stocked',
          is_read: false,
          is_prestocked: true,
        };

        // 1. Pop up live floating toast
        addToast(liveNotif);

        // 2. Prepend live notification to notifications list
        setNotifications((prev) => {
          const updated = prev.map((n) =>
            n.product_id === item.product_id || n.id === item.id
              ? { ...n, is_prestocked: true, can_prestock: false, is_read: true, badge: 'Buffer Stocked' }
              : n
          );
          if (!updated.some((n) => n.id === liveNotif.id)) {
            return [liveNotif, ...updated];
          }
          return updated;
        });

        // 3. Make Notification Button live
        setCounts((prev) => ({
          ...prev,
          festival_count: prev.festival_count + 1,
          unread_count: prev.unread_count + 1,
          total: prev.total + 1,
        }));

        playChime('festival');
        return res;
      }
    } catch (err) {
      console.error('Festival pre-stock action failed:', err);
    }
    return null;
  };

  // Mark All Read
  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setCounts((prev) => ({ ...prev, unread_count: 0 }));
    } catch (err) {
      console.error('Mark all read failed:', err);
    }
  };

  // Mark Single Read
  const handleMarkRead = async (notificationId) => {
    try {
      await api.markNotificationRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n))
      );
      setCounts((prev) => ({ ...prev, unread_count: Math.max(0, prev.unread_count - 1) }));
    } catch (err) {
      console.error('Mark read failed:', err);
    }
  };

  // Dismiss / Delete Notification
  const handleDismiss = async (notificationId) => {
    try {
      await api.dismissNotification(notificationId);
      setNotifications((prev) => prev.filter((n) => n.id !== notificationId));
      dismissToast(notificationId);
    } catch (err) {
      console.error('Dismiss failed:', err);
    }
  };

  // Trigger Live Simulation Alert
  const handleSimulate = async (type = 'stockout', details = {}) => {
    try {
      const res = await api.simulateNotification(type, details);
      if (res && res.notification) {
        // Will be delivered by WebSocket; in case WS is pending, also insert locally
        if (true) {
          handleLiveEvent({ event: `${type.toUpperCase()}_ALERT`, notification: res.notification });
        }
      }
      return res;
    } catch (err) {
      console.error('Simulation failed:', err);
      return null;
    }
  };

  const value = {
    notifications,
    counts,
    loading,
    isWsConnected,
    soundEnabled,
    toggleSound,
    liveToasts,
    addToast,
    dismissToast,
    handleRestock,
    handleMitigateWastage,
    handlePrestockFestival,
    handleMarkAllRead,
    handleMarkRead,
    handleDismiss,
    handleSimulate,
    nativePermission,
    requestNativeNotificationPermission,
    refreshNotifications: fetchNotifications,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useLiveNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useLiveNotifications must be used within a NotificationProvider');
  }
  return context;
}

