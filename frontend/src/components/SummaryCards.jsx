import React from 'react';
import { Target, Cpu, Activity, ArrowUpRight } from 'lucide-react';
import { motion } from 'framer-motion';

const SummaryCards = ({ stats = {} }) => {
  const safeStats = {
    todayActivity: stats?.todayActivity || '0',
    totalLeads: stats?.totalLeads || '0',
    activeAgents: stats?.activeAgents || '0',
  };

  const cards = [
    { 
      label: "Identified Intents", 
      value: safeStats.todayActivity, 
      icon: Activity, 
      color: 'text-amber-600', 
      bgColor: 'bg-amber-50',
      trend: 'LIVE', 
      trendLabel: 'real-time extraction' 
    },
    { 
      label: "Total Signals", 
      value: safeStats.totalLeads, 
      icon: Target, 
      color: 'text-blue-600', 
      bgColor: 'bg-blue-50',
      trend: 'ARCHIVE', 
      trendLabel: 'total historical' 
    },
    { 
      label: "Active Fleet", 
      value: safeStats.activeAgents, 
      icon: Cpu, 
      color: 'text-purple-600', 
      bgColor: 'bg-purple-50',
      trend: 'RUNNING', 
      trendLabel: 'agents patrolling' 
    },
  ];

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  };

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <motion.div 
            key={i} 
            variants={item}
            whileHover={{ 
              y: -8,
              transition: { duration: 0.3, ease: "easeOut" }
            }}
            className="bg-white border border-gray-100 p-6 rounded-2xl shadow-sm hover:shadow-md transition-all duration-300 group w-full md:w-[65%]"
          >
            <div className="flex justify-between items-start mb-4">
              <div className={`p-3 rounded-xl ${card.bgColor} ${card.color} transition-all duration-300`}>
                <Icon size={24} />
              </div>
              {card.trend.includes('+') && (
                <div className="flex items-center gap-1 text-green-600 bg-green-50 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border border-green-100">
                  <ArrowUpRight size={14} />
                  {card.trend}
                </div>
              )}
            </div>
            
            <div className="space-y-1">
              <p className="text-gray-400 text-[10px] font-bold uppercase tracking-widest">{card.label}</p>
              <h2 className="text-xl md:text-3xl font-bold text-gray-900 tracking-tight">{card.value}</h2>
            </div>
            
            <div className="flex items-center gap-2 mt-6 pt-4 border-t border-gray-50">
              <div className="flex items-center gap-2">
                {(card.trend === 'LIVE' || card.trend === 'RUNNING') && (
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                  </span>
                )}
                <span className={`text-[10px] font-bold uppercase tracking-widest ${
                  card.trend === 'LIVE' || card.trend === 'RUNNING' ? 'text-green-600' : 'text-gray-400'
                }`}>
                  {card.trend}
                </span>
              </div>
              <span className="text-[10px] text-gray-400 font-medium uppercase tracking-tight">{card.trendLabel}</span>
            </div>
          </motion.div>
        );
      })}
    </motion.div>
  );
};

export default SummaryCards;
