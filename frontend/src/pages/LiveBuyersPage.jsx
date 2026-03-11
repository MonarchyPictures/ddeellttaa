import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, Zap, Globe, MessageCircle, ShoppingBag, 
  Search, Phone, MapPin, ExternalLink, Flame, TrendingUp,
  Bell, RefreshCw, Filter
} from 'lucide-react';

/**
 * LIVE BUYERS PAGE - Apollo.io / Clay / ZoomInfo style experience
 * Full-page real-time buyer feed with dramatic visuals
 */
const LiveBuyersPage = () => {
  const [buyers, setBuyers] = useState([]);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [stats, setStats] = useState({
    totalToday: 0,
    hotLeads: 0,
    withPhone: 0
  });

  // Simulate real-time data
  useEffect(() => {
    const initialBuyers = generateMockBuyers(15);
    setBuyers(initialBuyers);
    updateStats(initialBuyers);

    const interval = setInterval(() => {
      if (Math.random() > 0.6) {
        const newBuyer = generateMockBuyers(1)[0];
        newBuyer.isNew = true;
        setBuyers(prev => [newBuyer, ...prev].slice(0, 50));
      }
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const updateStats = (data) => {
    const today = data.filter(b => {
      const time = new Date(b.timestamp).getTime();
      return Date.now() - time < 24 * 60 * 60 * 1000;
    }).length;
    const hot = data.filter(b => b.score >= 75).length;
    const withPhone = data.filter(b => b.hasPhone).length;
    setStats({ totalToday: today, hotLeads: hot, withPhone });
  };

  const filteredBuyers = buyers.filter(buyer => {
    if (selectedFilter === 'all') return true;
    if (selectedFilter === 'hot') return buyer.score >= 75;
    if (selectedFilter === 'phone') return buyer.hasPhone;
    return buyer.source.toLowerCase() === selectedFilter;
  });

  return (
    <div className="min-h-screen bg-[#050505] text-white">
      {/* Header */}
      <header className="border-b border-white/5 bg-[#0A0A0B]/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-[#050505] animate-pulse" />
              </div>
              <div>
                <h1 className="text-xl font-black tracking-tight">DELTA-9</h1>
                <p className="text-[10px] text-white/40 uppercase tracking-[0.2em]">Live Buyer Intelligence</p>
              </div>
            </div>

            <div className="hidden md:flex items-center gap-8">
              <StatBadge icon={Activity} label="Today" value={stats.totalToday} color="blue" pulse />
              <StatBadge icon={Flame} label="Hot" value={stats.hotLeads} color="red" />
              <StatBadge icon={Phone} label="Phone" value={stats.withPhone} color="green" />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Hero */}
        <div className="mb-8">
          <div className="flex items-end justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 rounded-full border border-green-500/30">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs font-bold text-green-400 uppercase">Live</span>
                </div>
              </div>
              <h2 className="text-4xl font-black">Live Buyers</h2>
              <p className="text-white/40 mt-2">Real-time buyer signals from across the web</p>
            </div>

            <div className="flex items-center gap-2">
              {['all', 'hot', 'phone'].map(filter => (
                <button
                  key={filter}
                  onClick={() => setSelectedFilter(filter)}
                  className={`
                    px-4 py-2 rounded-lg text-sm font-semibold transition-all
                    ${selectedFilter === filter ? 'bg-white text-black' : 'bg-white/5 text-white/60 hover:bg-white/10'}
                  `}
                >
                  {filter === 'all' ? 'All' : filter === 'hot' ? '🔥 Hot' : '📞 Phone'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Source Tabs */}
        <div className="flex items-center gap-2 mb-6">
          {[
            { id: 'all', label: 'All Sources', icon: Globe },
            { id: 'telegram', label: 'Telegram', icon: MessageCircle },
            { id: 'facebook', label: 'Facebook', icon: MessageCircle },
            { id: 'jiji', label: 'Jiji', icon: ShoppingBag },
            { id: 'reddit', label: 'Reddit', icon: MessageCircle },
            { id: 'google', label: 'Google', icon: Search },
          ].map(source => (
            <button
              key={source.id}
              onClick={() => setSelectedFilter(source.id)}
              className={`
                flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all
                ${selectedFilter === source.id
                  ? 'bg-white/10 text-white border border-white/20'
                  : 'bg-white/[0.02] text-white/40 border border-white/5 hover:bg-white/5'
                }
              `}
            >
              <source.icon className="w-4 h-4" />
              {source.label}
            </button>
          ))}
        </div>

        {/* Live Feed */}
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {filteredBuyers.map((buyer, index) => (
              <BuyerCard key={buyer.id} buyer={buyer} index={index} isLatest={index === 0} />
            ))}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

const StatBadge = ({ icon: Icon, label, value, color, pulse }) => {
  const colors = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
  };
  
  return (
    <div className={`flex items-center gap-3 px-4 py-2 rounded-xl border ${colors[color]}`}>
      <div className="relative">
        <Icon className="w-5 h-5" />
        {pulse && <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-current rounded-full animate-ping" />}
      </div>
      <div>
        <div className="text-xl font-black">{value}</div>
        <div className="text-[10px] uppercase tracking-wider opacity-70">{label}</div>
      </div>
    </div>
  );
};

const BuyerCard = ({ buyer, index, isLatest }) => {
  const getScoreBadge = (score) => {
    if (score >= 75) return { text: 'HOT', color: 'bg-red-500 text-white', icon: Flame };
    if (score >= 50) return { text: 'WARM', color: 'bg-amber-500 text-black', icon: TrendingUp };
    return { text: 'COLD', color: 'bg-blue-500/20 text-blue-400', icon: Activity };
  };

  const scoreBadge = getScoreBadge(buyer.score);
  const Icon = scoreBadge.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.03 }}
      className={`
        group relative bg-[#0A0A0B] rounded-xl border transition-all
        ${isLatest ? 'border-green-500/30 shadow-lg shadow-green-500/5' : 'border-white/5 hover:border-white/10'}
      `}
    >
      {buyer.isNew && (
        <motion.div className="absolute left-0 top-2 bottom-2 w-1 bg-gradient-to-b from-green-500 to-transparent rounded-full" />
      )}

      <div className="p-5">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-16">
            <div className={`flex items-center gap-1.5 text-xs font-bold ${buyer.isNew ? 'text-green-400' : 'text-white/30'}`}>
              {buyer.isNew && <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />}
              {buyer.time}
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-white font-semibold text-lg group-hover:text-blue-400 transition-colors">
              {buyer.text}
            </p>
            
            <div className="flex items-center gap-4 mt-2">
              <span className="flex items-center gap-1.5 text-sm text-white/50">
                <span className="text-lg">{buyer.sourceIcon}</span>
                {buyer.source}
              </span>
              {buyer.location && (
                <span className="flex items-center gap-1 text-sm text-white/40">
                  <MapPin size={14} /> {buyer.location}
                </span>
              )}
              {buyer.hasPhone && (
                <span className="flex items-center gap-1 text-sm text-green-400">
                  <Phone size={14} /> {buyer.phone}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-black text-sm ${scoreBadge.color}`}>
              <Icon size={14} />
              {scoreBadge.text}
              <span className="opacity-70 ml-1">{buyer.score}</span>
            </div>

            <a href={buyer.url} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm font-medium opacity-0 group-hover:opacity-100 transition-all">
              View <ExternalLink size={14} />
            </a>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

const generateMockBuyers = (count) => {
  const sources = [
    { name: 'Telegram', icon: '✈️' },
    { name: 'Facebook', icon: '📘' },
    { name: 'Jiji', icon: '🛒' },
    { name: 'Reddit', icon: '🔴' },
    { name: 'Google', icon: '🔍' }
  ];
  
  const requests = [
    'Looking for Toyota Vitz in Nairobi',
    'Need plumber in Westlands urgently',
    'Anyone selling tyres size 16?',
    'Buying iPhone 14 Pro Max',
    'Looking for 2 bedroom apartment in Kilimani',
    'Need laptop Dell i7 16GB RAM',
    'Buying maize wholesale - 100 bags',
    'Looking for graphic designer',
    'Need car mechanic in Mombasa',
    'Buying PS5 with games'
  ];
  
  const locations = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Westlands', 'Kilimani'];
  const phones = ['0712345678', '0723456789', '0734567890'];
  
  return Array.from({ length: count }, (_, i) => {
    const source = sources[Math.floor(Math.random() * sources.length)];
    const hasPhone = Math.random() > 0.3;
    const minutes = Math.floor(Math.random() * 60) + 1;
    
    return {
      id: `buyer-${Date.now()}-${i}`,
      text: requests[Math.floor(Math.random() * requests.length)],
      source: source.name,
      sourceIcon: source.icon,
      location: locations[Math.floor(Math.random() * locations.length)],
      hasPhone,
      phone: hasPhone ? phones[Math.floor(Math.random() * phones.length)] : null,
      score: Math.floor(Math.random() * 40) + 60,
      time: `${minutes}m ago`,
      timestamp: new Date(Date.now() - minutes * 60 * 1000).toISOString(),
      url: '#',
      isNew: false
    };
  });
};

export default LiveBuyersPage;
