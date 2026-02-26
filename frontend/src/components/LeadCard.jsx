import React, { useState } from 'react';
import {
  Phone,
  Bookmark,
  ExternalLink,
  MapPin,
  Clock,
  Flame,
  ShieldCheck,
  Mail,
  MessageCircle,
  User,
  Trash2,
  Zap,
  Globe,
  Activity,
  Share2,
  Copy,
  Check
} from 'lucide-react';
import { motion } from 'framer-motion';
import getApiUrl, { getApiKey } from '../config';

const LeadCard = ({ lead, onSave, onDelete, onClick, onStatusChange, onTap }) => {
  const [copied, setCopied] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [localOutreach, setLocalOutreach] = useState(lead.outreach_suggestion);

  const timeAgo = (date) => {
    if (!date) return "N/A";
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + "y ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + "mo ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + "d ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + "h ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + "m ago";
    return Math.floor(seconds) + "s ago";
  };

  const getStatusColor = (status) => {
    const s = status?.toLowerCase() || 'new';
    switch (s) {
      case 'new': return 'text-green-500 bg-green-500/10 border-green-500/20';
      case 'contacted': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'replied': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
      case 'negotiating': return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
      case 'converted': return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
      case 'dead': return 'text-red-500 bg-red-500/10 border-red-500/20';
      default: return 'text-gray-500 bg-gray-500/10 border-gray-500/20';
    }
  };

  const getMatchCue = (score, badge) => {
    // Priority: Use backend badge if available
    if (badge === 'HOT') return { icon: "🔥", label: "HOT BUYER", color: "text-red-500", border: "border-red-500/30", bg: "bg-red-500/10" };
    if (badge === 'WARM') return { icon: "☀️", label: "WARM LEAD", color: "text-yellow-500", border: "border-yellow-500/30", bg: "bg-yellow-500/10" };
    if (badge === 'COLD') return { icon: "❄️", label: "COLD", color: "text-blue-300", border: "border-blue-300/30", bg: "bg-blue-500/10" };

    // Fallback to score
    const s = score || 0;
    if (s >= 0.7) return { icon: "🔥", label: "HOT BUYER", color: "text-red-500", border: "border-red-500/30", bg: "bg-red-500/10" };
    if (s >= 0.4) return { icon: "☀️", label: "WARM LEAD", color: "text-yellow-500", border: "border-yellow-500/30", bg: "bg-yellow-500/10" };
    return { icon: "❄️", label: "COLD", color: "text-blue-300", border: "border-blue-300/30", bg: "bg-blue-500/10" };
  };

  // Robust Field Access (Matches Dashboard.jsx)
  // Standardized Fields: buyer_name, title, price, location, phone, source, intent_score
  const timestamp = lead.timestamp || lead.request_timestamp || lead.created_at;
  const isRecent = timestamp && (new Date() - new Date(timestamp)) < 24 * 60 * 60 * 1000;
  
  const score = lead.intent_score || lead.score || lead.buyer_match_score || 0;
  const badge = lead.badge || lead.lead_badge;
  
  const isHighIntent = badge === 'HOT' || score >= 0.7;
  const matchCue = getMatchCue(score, badge);

  const whatsappLink = lead.whatsapp_url || lead.whatsapp_link;
  const hasWhatsApp = !!whatsappLink;
  
  // Standardized field mapping
  const buyerName = lead.buyer_name || lead.source || "Market Signal";
  const title = lead.title || lead.product || "General Request";
  const price = lead.price ? `KES ${parseInt(lead.price).toLocaleString()}` : "Price Negotiable";
  const location = lead.location || "Kenya";
  const phone = lead.phone || lead.contact_phone;
  const source = lead.source || "Web";
  const intentScore = lead.intent_score || 0.4;

  const intentText = lead.buyer_request_snippet || lead.buyer_intent_quote || lead.intent || title;
  const sourceUrl = lead.source_url || lead.url;
  
  const displayPhone = (phone) => {
    if (!phone) return null;
    // Handle format 2547XXXXXXXX
    if (phone.startsWith('254') && phone.length === 12) {
      return `+254 ${phone.slice(3, 5)} ${phone.slice(5, 8)} ${phone.slice(8)}`;
    }
    return phone;
  };


  const handleContact = async (e) => {
    e.stopPropagation();
    
    // Always prioritize one-click WhatsApp if we have a contact
    if (hasWhatsApp) {
      setIsGenerating(true);
      try {
        const apiUrl = getApiUrl();
        const apiKey = getApiKey();
        
        // Fetch the prefilled WhatsApp URL from the backend
        const response = await fetch(`${apiUrl}/outreach/${lead.lead_id}/whatsapp`, {
          headers: { 'X-API-Key': apiKey }
        });

        if (response.ok) {
          const data = await response.json();
          window.open(data.url, '_blank');
          if (onTap) {
            onTap(lead.lead_id || lead.id);
          } else {
            onStatusChange && onStatusChange(lead.lead_id || lead.id, 'contacted');
          }
        } else {
          // Fallback if the endpoint fails but we have a direct link
          if (whatsappLink) {
            window.open(whatsappLink, '_blank');
            if (onTap) {
              onTap(lead.lead_id || lead.id);
            } else {
              onStatusChange && onStatusChange(lead.lead_id || lead.id, 'contacted');
            }
          }
        }
      } catch (err) {
        console.error("Outreach error:", err);
        // Fallback to direct link on error
        if (whatsappLink) {
          window.open(whatsappLink, '_blank');
          if (onTap) {
            onTap(lead.lead_id || lead.id);
          } else {
            onStatusChange && onStatusChange(lead.lead_id || lead.id, 'contacted');
          }
        }
      } finally {
        setIsGenerating(false);
      }
    } else if (lead.source_url) {
      window.open(lead.source_url, '_blank');
    }
  };

  const handleCopyOutreach = (e) => {
    e.stopPropagation();
    const textToCopy = localOutreach || lead.outreach_suggestion;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleGenerateOutreach = async (e) => {
    e.stopPropagation();
    setIsGenerating(true);
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const res = await fetch(`${apiUrl}/outreach/${lead.lead_id}`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey
        }
      });
      if (res.ok) {
        const data = await res.json();
        setLocalOutreach(data.message);
      }
    } catch (err) {
      console.error("Outreach generation failed:", err);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      onClick={() => handleContact({ stopPropagation: () => {} })}
      className="bg-[#0A0A0B] border border-white/5 rounded-3xl p-6 relative group hover:border-blue-500/30 transition-all duration-300 shadow-2xl cursor-pointer"
    >
      <div className="relative z-10">
        {/* Header - Tags + Time */}
        <div className="flex flex-col md:flex-row justify-between items-start gap-2 mb-6">
          <div className="flex flex-wrap gap-2">
            {isHighIntent && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-red-500/30 bg-red-500/10 text-red-500 flex items-center gap-1">
                🔥 High intent
              </span>
            )}
            {hasWhatsApp && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-green-500/30 bg-green-500/10 text-green-500 flex items-center gap-1">
                💬 WhatsApp
              </span>
            )}
            {isRecent && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-blue-500/30 bg-blue-500/10 text-blue-500 flex items-center gap-1">
                ⏱ Recent
              </span>
            )}
            {lead.is_verified && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-blue-500/30 bg-blue-500/10 text-blue-500 flex items-center gap-1">
                <ShieldCheck size={10} />
                VERIFIED
              </span>
            )}
            {lead.tap_count > 0 && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-blue-500/30 bg-blue-500/10 text-blue-500 flex items-center gap-1">
                <Activity size={10} />
                TAPS: {lead.tap_count}
              </span>
            )}
          </div>
          <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest flex items-center gap-1">
            <Clock size={10} />
            {timeAgo(timestamp)}
          </span>
        </div>

        {/* User Info - ENRICHED */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white font-black text-sm italic">
            {buyerName?.charAt(0) || 'B'}
          </div>
          <div>
            <div className="text-white font-bold text-sm flex items-center gap-2">
              {buyerName}
              {(phone) && <span className="text-green-500"><ShieldCheck size={12} /></span>}
            </div>
            <div className="text-white/40 text-[10px] font-black uppercase tracking-widest">
              <p className="text-green-400 font-medium"> 
                {phone ? (
                  <a 
                    href={`tel:${phone}`} 
                    className="hover:text-green-300 transition-colors flex items-center gap-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    📞 {displayPhone(phone)}
                  </a>
                ) : (
                  "📞 No phone found"
                )}
              </p> 
            </div>
          </div>
        </div>

        {/* Product + Intent Text - READ */}
        <div className="mb-4">
          <div className="text-blue-500 text-[11px] font-black uppercase tracking-[0.2em] mb-1">{title}</div>
          <h3 className="text-white font-black text-xl leading-tight group-hover:text-blue-400 transition-colors italic">
            "{intentText}"
          </h3>
          <p className="text-white/60 text-xs font-bold mt-1">
             💰 {price}
          </p>
          {lead.buyer_request_snippet && lead.buyer_request_snippet !== intentText && (
            <p className="text-white/40 text-xs mt-2 line-clamp-2 italic font-medium leading-relaxed">
              ...{lead.buyer_request_snippet.substring(0, 150)}...
            </p>
          )}
        </div>

        {/* Location + Source */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="flex items-center gap-1.5 text-white/60 text-xs font-bold">
            <MapPin size={14} className="text-blue-500" />
            <span>{location}</span>
            {lead.distance_km > 0 && (
              <span className="text-white/30 ml-1">({lead.distance_km}km)</span>
            )}
          </div>
          <div className="flex items-center gap-1.5 text-white/40 text-[10px] font-black uppercase tracking-widest">
            <span>{source}</span>
          </div>
          <div className="flex items-center gap-1.5 text-white/40 text-[10px] font-black uppercase tracking-widest">
            <span className={isHighIntent ? "text-green-500" : "text-yellow-500"}>Score: {Math.round(intentScore * 100)}%</span>
          </div>
          {sourceUrl && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                window.open(sourceUrl, '_blank');
              }}
              className="ml-auto text-blue-500 hover:text-blue-400 text-[10px] font-black uppercase tracking-widest flex items-center gap-1 transition-colors cursor-pointer"
            >
              <ExternalLink size={12} />
              SOURCE
            </button>
          )}
        </div>

        {/* Suggested Outreach Section */}
        {(localOutreach || lead.outreach_suggestion) && (
          <div className="bg-slate-900 p-4 rounded-xl mt-4 border border-slate-700"> 
            <div className="flex justify-between items-center mb-2"> 
              <span className="text-sm text-slate-400"> 
                ✨ AI Outreach Signal 
              </span> 
            </div> 
            <p className="text-slate-200 italic"> 
              {localOutreach || lead.outreach_suggestion} 
            </p> 
          </div>
        )}

        {/* Primary Actions - TAP + COPY */}
        <div className="flex flex-col md:flex-row gap-3">
          {hasWhatsApp ? (
            <button
              onClick={handleContact}
              disabled={isGenerating}
              className="flex-1 bg-green-600 hover:bg-green-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-3 uppercase tracking-widest transition-all active:scale-95 shadow-lg shadow-green-600/20 disabled:opacity-50 cursor-pointer"
            >
              {isGenerating ? <Activity size={20} className="animate-spin" /> : <MessageCircle size={20} fill="white" />}
              {isGenerating ? 'CONNECTING...' : 'TAP TO WHATSAPP'}
            </button>
          ) : lead.source_url ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                window.open(lead.source_url, '_blank');
              }}
              className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-3 uppercase tracking-widest transition-all active:scale-95 shadow-lg shadow-blue-600/20 cursor-pointer"
            >
              <ExternalLink size={20} />
              OPEN SOURCE PLATFORM
            </button>
          ) : (
            <div className="flex-1 flex flex-col gap-2">
              <button
                disabled
                className="w-full bg-white/5 text-white/20 font-black text-xs py-4 rounded-xl flex items-center justify-center gap-2 uppercase tracking-widest cursor-not-allowed border border-white/5"
              >
                <MessageCircle size={16} />
                NO CONTACT LINK
              </button>
            </div>
          )}

          <button
            onClick={handleContact}
            disabled={isGenerating || !hasWhatsApp}
            className={`px-6 py-4 rounded-xl font-black text-sm uppercase tracking-widest transition-all active:scale-95 flex items-center justify-center gap-2 ${
              hasWhatsApp 
                ? 'bg-green-600/20 border border-green-500/30 text-green-500 hover:bg-green-600/30 hover:text-green-400 cursor-pointer' 
                : 'bg-white/5 border border-white/10 text-white/20 cursor-not-allowed'
            }`}
          >
            <MessageCircle size={18} />
            {hasWhatsApp ? '💬 WHATSAPP BUYER' : 'NO CONTACT'}
          </button>

          {phone && (
            <a
              href={`tel:${phone}`}
              onClick={(e) => e.stopPropagation()}
              className="px-6 py-4 rounded-xl font-black text-sm uppercase tracking-widest transition-all active:scale-95 flex items-center justify-center gap-2 bg-blue-600/20 border border-blue-500/30 text-blue-500 hover:bg-blue-600/30 hover:text-blue-400 cursor-pointer"
            >
              <Phone size={18} />
              CALL
            </a>
          )}

          <button
            onClick={async (e) => {
              e.stopPropagation();
              setIsGenerating(true);
              try {
                const apiUrl = getApiUrl();
                const apiKey = getApiKey();
                const res = await fetch(`${apiUrl}/outreach/${lead.lead_id}`, {
                  method: 'POST',
                  headers: { 'X-API-Key': apiKey }
                });
                if (res.ok) {
                  const data = await res.json();
                  await navigator.clipboard.writeText(data.message);
                  setLocalOutreach(data.message);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }
              } catch (err) {
                console.error("Instant outreach failed:", err);
              } finally {
                setIsGenerating(false);
              }
            }}
            disabled={isGenerating}
            className={`px-6 py-4 rounded-xl border font-black text-sm uppercase tracking-widest transition-all active:scale-95 flex items-center gap-2 ${
              copied 
                ? 'bg-green-500/20 border-green-500 text-green-500' 
                : 'bg-white/5 border-white/10 text-white/60 hover:bg-white/10 hover:text-white'
            }`}
          >
            {copied ? <Check size={18} /> : isGenerating ? <Activity size={18} className="animate-spin" /> : <Mail size={18} />}
            {copied ? 'COPIED' : '📩 COPY OUTREACH'}
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default LeadCard;
