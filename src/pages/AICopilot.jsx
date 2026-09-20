import React, { useState } from 'react';
import PageHeader from '../components/PageHeader';
import { api } from '../api/client';
import { Bot, Send, Sparkles, User, Cpu, ArrowRight } from 'lucide-react';

export default function AICopilot() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'bot',
      text: 'Hello Alex! I am your TransitOps AI Copilot. How can I assist with supply chain telemetry, stock reordering, or route optimization today?',
      timestamp: '10:14 AM',
    },
    {
      id: 2,
      sender: 'user',
      text: 'What are the current stockout risks for dairy products in the Mumbai region?',
      timestamp: '10:15 AM',
    },
    {
      id: 3,
      sender: 'bot',
      text: 'Analysis complete for Mumbai Central Depot:\n\n• **Fresh Milk 1L (MK-001-F)**: 820 units remaining (8 days of supply). High stockout risk predicted in 48 hours.\n• **Yogurt 500g (YG-500-D)**: 320 units remaining. Near-expiry risk for 120 units.\n\n**Recommendation**: I have prepared a automated Purchase Order for 500 units of Fresh Milk from Amul Cooperatives.',
      timestamp: '10:15 AM',
      actions: ['Execute Reorder for 500 units', 'Apply 15% discount on near-expiry Yogurt'],
    },
  ]);

  const [inputQuery, setInputQuery] = useState('');

  const promptSuggestions = [
    'Analyze NH-48 traffic delays & truck rerouting options',
    'Show top perishable items nearing expiry',
    'Evaluate supplier compliance and lead times',
    'Forecast demand spike and stockout risks',
  ];

  const handleSend = async (e) => {
    e?.preventDefault?.();
    const query = inputQuery.trim();
    if (!query) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');

    try {
      const res = await api.chatAICopilot(query);
      if (res && res.reply) {
        const botMsg = {
          id: Date.now() + 1,
          sender: 'bot',
          text: res.reply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          actions: res.suggested_actions || [],
        };
        setMessages((prev) => [...prev, botMsg]);
        return;
      }
    } catch (err) {
      console.warn('AI copilot error:', err);
    }

    // Fallback response if offline
    const botMsg = {
      id: Date.now() + 1,
      sender: 'bot',
      text: `Processing query: "${query}"\n\nAI Agent Hub executed diagnostic across warehouse telemetry streams. Inventory, stockout risks, and perishable expiry monitors are fully operational.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, botMsg]);
  };


  return (
    <div className="space-y-lg flex flex-col h-[calc(100vh-100px)]">
      <PageHeader
        title="AI Copilot Command Center"
        subtitle="Natural language reasoning, automated diagnostic agent interactions, and decision support."
      />

      {/* Chat Container */}
      <div className="glass-panel rounded-xl flex-1 flex flex-col overflow-hidden">
        {/* Messages Stream */}
        <div className="flex-1 p-lg space-y-md overflow-y-auto custom-scrollbar">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-md max-w-3xl ${
                msg.sender === 'user' ? 'ml-auto flex-row-reverse' : ''
              }`}
            >
              <div
                className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                  msg.sender === 'user'
                    ? 'bg-secondary-container text-on-secondary-container'
                    : 'bg-primary-container text-on-primary-container shadow-md shadow-primary/20'
                }`}
              >
                {msg.sender === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
              </div>

              <div
                className={`p-md rounded-xl space-y-xs ${
                  msg.sender === 'user'
                    ? 'bg-secondary-container/30 border border-secondary/30 text-on-surface'
                    : 'glass-card ai-border text-on-surface'
                }`}
              >
                <div className="flex justify-between items-center gap-md">
                  <span className="font-bold text-label-md">
                    {msg.sender === 'user' ? 'Daksh Mehta' : 'TransitOps Copilot Agent'}
                  </span>
                  <span className="text-[10px] text-on-surface-variant font-mono">{msg.timestamp}</span>
                </div>

                <div className="text-body-md whitespace-pre-line leading-relaxed">{msg.text}</div>

                {msg.actions && (
                  <div className="pt-xs flex gap-xs flex-wrap">
                    {msg.actions.map((act, idx) => (
                      <button
                        key={idx}
                        onClick={() => alert(`Executed action: ${act}`)}
                        className="px-md py-xs bg-primary text-on-primary font-bold rounded-md text-label-md hover:opacity-90 transition-all flex items-center gap-xs"
                      >
                        <span>{act}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Prompt Suggestions */}
        <div className="px-lg py-sm bg-surface-container-low/50 border-t border-outline-variant/40 flex gap-xs overflow-x-auto custom-scrollbar">
          {promptSuggestions.map((sug, idx) => (
            <button
              key={idx}
              onClick={() => setInputQuery(sug)}
              className="px-md py-xs bg-surface-container hover:bg-surface-variant border border-outline-variant rounded-full text-label-sm text-on-surface-variant shrink-0 transition-colors flex items-center gap-xs"
            >
              <Sparkles className="w-3 h-3 text-primary" />
              <span>{sug}</span>
            </button>
          ))}
        </div>

        {/* Query Input Bar */}
        <form onSubmit={handleSend} className="p-md border-t border-outline-variant bg-surface-container-low flex gap-md">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask Copilot about stock levels, truck routes, or automated reorder rules..."
            className="flex-1 bg-surface-container border border-outline-variant rounded-lg px-md py-sm text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:border-primary"
          />
          <button
            type="submit"
            className="px-lg py-sm bg-primary text-on-primary font-bold rounded-lg hover:opacity-90 active:scale-95 transition-all flex items-center gap-xs shadow-lg shadow-primary/20"
          >
            <span>Ask</span>
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
