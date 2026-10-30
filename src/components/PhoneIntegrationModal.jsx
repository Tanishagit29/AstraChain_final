import React, { useState, useEffect } from 'react';
import {
  Smartphone, QrCode, Bell, Send, CheckCircle2, Copy, Check,
  ExternalLink, X, ShieldAlert, Zap, Clock, Sparkles, AlertTriangle,
  RotateCw, MessageSquare, Radio, Download
} from 'lucide-react';
import { api } from '../api/client';
import { useLiveNotifications } from '../context/NotificationContext';

export default function PhoneIntegrationModal({ isOpen, onClose }) {
  const [configData, setConfigData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [copiedTopic, setCopiedTopic] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testSuccess, setTestSuccess] = useState(null);
  const [activeTab, setActiveTab] = useState('push'); // 'push', 'qr', 'telegram'

  const [topicName, setTopicName] = useState('astrachain-daksh-alert');
  const [notifyStockout, setNotifyStockout] = useState(true);
  const [notifyRestock, setNotifyRestock] = useState(true);
  const [notifyWastage, setNotifyWastage] = useState(true);
  const [notifyFestival, setNotifyFestival] = useState(true);
  const [telegramEnabled, setTelegramEnabled] = useState(false);
  const [telegramToken, setTelegramToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [saving, setSaving] = useState(false);

  const { nativePermission, requestNativeNotificationPermission } = useLiveNotifications();

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    api.getPhoneConfig().then((res) => {
      if (res && res.success) {
        setConfigData(res);
        if (res.config) {
          setTopicName(res.config.ntfy_topic || 'astrachain-daksh-alert');
          setNotifyStockout(res.config.notify_stockout !== false);
          setNotifyRestock(res.config.notify_restock !== false);
          setNotifyWastage(res.config.notify_wastage !== false);
          setNotifyFestival(res.config.notify_festival !== false);
          setTelegramEnabled(Boolean(res.config.telegram_enabled));
          setTelegramToken(res.config.telegram_bot_token || '');
          setTelegramChatId(res.config.telegram_chat_id || '');
        }
      }
      setLoading(false);
    });
  }, [isOpen]);

  if (!isOpen) return null;

  const localIp = configData?.local_ip || '192.168.29.124';
  const mobileWebUrl = configData?.mobile_web_url || `http://${localIp}:5173`;
  const ntfyUrl = `https://ntfy.sh/${topicName}`;

  const copyToClipboard = (text, type = 'url') => {
    navigator.clipboard?.writeText(text);
    if (type === 'url') {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } else {
      setCopiedTopic(true);
      setTimeout(() => setCopiedTopic(false), 2500);
    }
  };

  const handleSendTestPush = async (alertType = 'stockout') => {
    setTesting(true);
    setTestSuccess(null);
    try {
      const res = await api.sendTestPhonePush(alertType);
      if (res && res.success) {
        setTestSuccess(`Test alert pushed to your phone via ${topicName}!`);
        setTimeout(() => setTestSuccess(null), 5000);
      }
    } catch (e) {
      console.error('Test push error:', e);
    } finally {
      setTesting(false);
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await api.updatePhoneConfig({
        ntfy_topic: topicName.trim(),
        notify_stockout: notifyStockout,
        notify_restock: notifyRestock,
        notify_wastage: notifyWastage,
        notify_festival: notifyFestival,
        telegram_enabled: telegramEnabled,
        telegram_bot_token: telegramToken.trim(),
        telegram_chat_id: telegramChatId.trim(),
      });
      setTestSuccess('Phone preferences saved successfully!');
      setTimeout(() => setTestSuccess(null), 3500);
    } catch (e) {
      console.error('Save error:', e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div className="bg-surface/95 backdrop-blur-2xl border border-outline-variant/80 rounded-2xl w-full max-w-xl shadow-2xl flex flex-col overflow-hidden max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 border-b border-outline-variant/60 bg-surface-container-low flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
              <Smartphone className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-bold text-on-surface text-[15px] flex items-center gap-2">
                Phone & Mobile Alerts Integration
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  Live Sync
                </span>
              </h3>
              <p className="text-[11px] text-on-surface-variant font-mono">
                Get real-time push alerts and 1-click actions directly on your phone
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-4 py-2 border-b border-outline-variant/40 bg-surface-container-lowest/50 flex items-center gap-2 text-[12px] font-medium">
          <button
            onClick={() => setActiveTab('push')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'push'
                ? 'bg-primary text-on-primary font-bold shadow'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <Bell className="w-3.5 h-3.5" />
            <span>Instant Phone Push</span>
          </button>
          <button
            onClick={() => setActiveTab('qr')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'qr'
                ? 'bg-primary text-on-primary font-bold shadow'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <QrCode className="w-3.5 h-3.5" />
            <span>Scan Mobile App QR</span>
          </button>
          <button
            onClick={() => setActiveTab('telegram')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'telegram'
                ? 'bg-primary text-on-primary font-bold shadow'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Telegram Bot</span>
          </button>
        </div>

        {/* Success Banner */}
        {testSuccess && (
          <div className="p-3 bg-emerald-500/15 border-b border-emerald-500/30 text-emerald-400 text-[12px] font-bold flex items-center gap-2 animate-fade-in">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{testSuccess}</span>
          </div>
        )}

        {/* Modal Scrollable Body */}
        <div className="p-5 flex-1 overflow-y-auto space-y-5 custom-scrollbar text-[13px]">
          {activeTab === 'push' && (
            <div className="space-y-4">
              <div className="p-3 bg-primary/10 border border-primary/20 rounded-xl space-y-1">
                <p className="font-bold text-primary flex items-center gap-1.5">
                  <Radio className="w-4 h-4" /> Real-Time Lock Screen Notifications
                </p>
                <p className="text-[12px] text-on-surface-variant leading-relaxed">
                  Every time a stockout happens, an item is restocked, shelf-life is expiring, or a festival surge is detected,
                  your phone will ring, vibrate, and show the notification with interactive 1-click action buttons.
                </p>
              </div>

              {/* NTFY Topic Configuration */}
              <div className="space-y-2">
                <label className="font-mono text-label-sm text-on-surface-variant uppercase font-bold block">
                  Your Phone Notification Channel
                </label>
                <div className="flex gap-2">
                  <div className="flex-1 flex items-center bg-surface-container-low border border-outline-variant rounded-xl px-3 py-2 font-mono text-on-surface text-[12px]">
                    <span className="text-on-surface-variant/70">https://ntfy.sh/</span>
                    <input
                      type="text"
                      value={topicName}
                      onChange={(e) => setTopicName(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ''))}
                      className="bg-transparent text-primary font-bold focus:outline-none flex-1 ml-0.5"
                      placeholder="custom-topic"
                    />
                  </div>
                  <button
                    onClick={() => copyToClipboard(ntfyUrl, 'topic')}
                    className="p-2.5 rounded-xl border border-outline-variant hover:bg-surface-container-high text-on-surface-variant transition-colors cursor-pointer"
                    title="Copy topic link"
                  >
                    {copiedTopic ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <a
                    href={ntfyUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2.5 rounded-xl bg-primary text-on-primary font-bold hover:opacity-90 transition-all flex items-center gap-1 cursor-pointer"
                    title="Open channel in web browser"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
                <p className="text-[11px] text-on-surface-variant font-mono">
                  Tip: Open this link on your phone or subscribe inside the free <strong>NTFY App</strong> on Android or iOS.
                </p>
              </div>

              {/* Instant Test Buttons */}
              <div className="space-y-2 pt-2 border-t border-outline-variant/30">
                <label className="font-mono text-label-sm text-on-surface-variant uppercase font-bold block">
                  Send Test Alert to Phone Right Now
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <button
                    onClick={() => handleSendTestPush('stockout')}
                    disabled={testing}
                    className="p-2 rounded-xl bg-error/15 hover:bg-error/25 text-error border border-error/30 font-bold text-[11px] flex flex-col items-center gap-1 transition-all cursor-pointer disabled:opacity-50"
                  >
                    <Zap className="w-4 h-4" />
                    <span>Stockout Alert</span>
                  </button>
                  <button
                    onClick={() => handleSendTestPush('restock')}
                    disabled={testing}
                    className="p-2 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/30 font-bold text-[11px] flex flex-col items-center gap-1 transition-all cursor-pointer disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Restock Alert</span>
                  </button>
                  <button
                    onClick={() => handleSendTestPush('wastage')}
                    disabled={testing}
                    className="p-2 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 text-amber-400 border border-amber-500/30 font-bold text-[11px] flex flex-col items-center gap-1 transition-all cursor-pointer disabled:opacity-50"
                  >
                    <Clock className="w-4 h-4" />
                    <span>Wastage Alert</span>
                  </button>
                  <button
                    onClick={() => handleSendTestPush('festival')}
                    disabled={testing}
                    className="p-2 rounded-xl bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/30 font-bold text-[11px] flex flex-col items-center gap-1 transition-all cursor-pointer disabled:opacity-50"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>Festival Alert</span>
                  </button>
                </div>
              </div>

              {/* Native Mobile Browser Push */}
              <div className="p-3 bg-surface-container-high/40 border border-outline-variant/60 rounded-xl flex items-center justify-between gap-3">
                <div>
                  <h4 className="font-bold text-on-surface text-[12px] flex items-center gap-1.5">
                    <Bell className="w-4 h-4 text-primary" /> Browser Native Phone Push
                  </h4>
                  <p className="text-[11px] text-on-surface-variant">
                    {nativePermission === 'granted'
                      ? '✓ Native browser lock screen notifications are enabled'
                      : 'Request permission to show native mobile notification popups'}
                  </p>
                </div>
                {nativePermission !== 'granted' ? (
                  <button
                    onClick={requestNativeNotificationPermission}
                    className="px-3 py-1.5 bg-primary text-on-primary font-bold rounded-lg text-[11px] hover:opacity-90 active:scale-95 transition-all shadow shrink-0 cursor-pointer"
                  >
                    Enable Now
                  </button>
                ) : (
                  <span className="text-emerald-400 font-bold text-[11px] font-mono bg-emerald-500/15 px-2 py-1 rounded-md border border-emerald-500/30">
                    Active
                  </span>
                )}
              </div>
            </div>
          )}

          {activeTab === 'qr' && (
            <div className="space-y-4 text-center">
              <div className="p-3 bg-surface-container-high/40 rounded-xl text-left text-[12px] text-on-surface-variant">
                <p>
                  Connect your phone to the same Wi-Fi network and scan this QR code with your phone camera to open the
                  live AstraChain Manager portal on your phone.
                </p>
              </div>

              {/* Dynamic QR Code */}
              <div className="flex flex-col items-center justify-center p-4 bg-white rounded-2xl shadow-xl border border-outline-variant max-w-xs mx-auto">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(mobileWebUrl)}`}
                  alt="AstraChain Mobile Access QR Code"
                  className="w-48 h-48 rounded-lg"
                  loading="lazy"
                />
                <span className="text-slate-800 font-mono font-bold text-[11px] mt-2">
                  Scan to Open on Phone
                </span>
              </div>

              {/* Local Wi-Fi Link */}
              <div className="flex items-center justify-center gap-2 max-w-md mx-auto">
                <input
                  type="text"
                  readOnly
                  value={mobileWebUrl}
                  className="bg-surface-container-low border border-outline-variant rounded-xl px-3 py-2 font-mono text-[12px] text-primary font-bold text-center flex-1"
                />
                <button
                  onClick={() => copyToClipboard(mobileWebUrl, 'url')}
                  className="p-2.5 rounded-xl border border-outline-variant hover:bg-surface-container-high text-on-surface-variant transition-colors cursor-pointer"
                  title="Copy mobile URL"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'telegram' && (
            <div className="space-y-4">
              <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl space-y-1">
                <p className="font-bold text-blue-400 flex items-center gap-1.5">
                  <MessageSquare className="w-4 h-4" /> Telegram Mobile Bot
                </p>
                <p className="text-[12px] text-on-surface-variant">
                  Optionally receive all notifications directly in your Telegram phone app. Create a bot with{' '}
                  <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer" className="text-primary underline">
                    @BotFather
                  </a>{' '}
                  and enter credentials below.
                </p>
              </div>

              <label className="flex items-center gap-2 text-on-surface cursor-pointer text-[12px] font-bold">
                <input
                  type="checkbox"
                  checked={telegramEnabled}
                  onChange={(e) => setTelegramEnabled(e.target.checked)}
                  className="accent-primary w-4 h-4 rounded"
                />
                Enable Telegram Phone Notifications
              </label>

              {telegramEnabled && (
                <div className="space-y-3 pt-2">
                  <div>
                    <label className="font-mono text-[11px] text-on-surface-variant block mb-1">
                      Telegram Bot Token
                    </label>
                    <input
                      type="text"
                      value={telegramToken}
                      onChange={(e) => setTelegramToken(e.target.value)}
                      placeholder="123456789:ABCdefGhIJKlmNoPQRstuVWXyz"
                      className="w-full bg-surface-container-low border border-outline-variant rounded-xl px-3 py-2 text-body-md text-on-surface font-mono text-[12px]"
                    />
                  </div>
                  <div>
                    <label className="font-mono text-[11px] text-on-surface-variant block mb-1">
                      Your Telegram Chat ID
                    </label>
                    <input
                      type="text"
                      value={telegramChatId}
                      onChange={(e) => setTelegramChatId(e.target.value)}
                      placeholder="e.g. 987654321"
                      className="w-full bg-surface-container-low border border-outline-variant rounded-xl px-3 py-2 text-body-md text-on-surface font-mono text-[12px]"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Alert Category Preferences */}
          <div className="pt-3 border-t border-outline-variant/30 space-y-2">
            <label className="font-mono text-label-sm text-on-surface-variant uppercase font-bold block">
              Active Alerts Sent to Phone
            </label>
            <div className="grid grid-cols-2 gap-2 text-[12px]">
              <label className="flex items-center gap-2 cursor-pointer bg-surface-container-low p-2 rounded-lg border border-outline-variant/40">
                <input
                  type="checkbox"
                  checked={notifyStockout}
                  onChange={(e) => setNotifyStockout(e.target.checked)}
                  className="accent-primary w-4 h-4 rounded"
                />
                <span>🚨 Stockouts</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer bg-surface-container-low p-2 rounded-lg border border-outline-variant/40">
                <input
                  type="checkbox"
                  checked={notifyRestock}
                  onChange={(e) => setNotifyRestock(e.target.checked)}
                  className="accent-primary w-4 h-4 rounded"
                />
                <span>📦 Restocks</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer bg-surface-container-low p-2 rounded-lg border border-outline-variant/40">
                <input
                  type="checkbox"
                  checked={notifyWastage}
                  onChange={(e) => setNotifyWastage(e.target.checked)}
                  className="accent-primary w-4 h-4 rounded"
                />
                <span>⚠️ Wastage Expiry</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer bg-surface-container-low p-2 rounded-lg border border-outline-variant/40">
                <input
                  type="checkbox"
                  checked={notifyFestival}
                  onChange={(e) => setNotifyFestival(e.target.checked)}
                  className="accent-primary w-4 h-4 rounded"
                />
                <span>🎪 Festival Surges</span>
              </label>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-3 bg-surface-container-low border-t border-outline-variant/60 flex items-center justify-between">
          <span className="font-mono text-[11px] text-on-surface-variant flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            NTFY Live Gateway Connected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors cursor-pointer text-[12px]"
            >
              Close
            </button>
            <button
              onClick={handleSaveConfig}
              disabled={saving}
              className="px-4 py-1.5 rounded-lg bg-primary text-on-primary font-bold hover:opacity-90 active:scale-95 transition-all text-[12px] flex items-center gap-1.5 shadow-md cursor-pointer disabled:opacity-50"
            >
              {saving ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
              <span>Save Settings</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

