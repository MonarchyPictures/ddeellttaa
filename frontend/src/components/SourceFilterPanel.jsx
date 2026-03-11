import React, { useState, useEffect } from 'react';
import { Filter, X, Check, Globe, Clock, MessageCircle, ShoppingBag, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const SourceFilterPanel = ({ onFilterChange, initialFilters = {} }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  
  // Source filters
  const [selectedSources, setSelectedSources] = useState(initialFilters.sources || [
    'telegram', 'facebook', 'jiji', 'reddit', 'google'
  ]);
  
  // Freshness filters
  const [selectedFreshness, setSelectedFreshness] = useState(initialFilters.freshness || [
    '24h', '3d', '7d'
  ]);

  const sources = [
    { id: 'telegram', label: 'Telegram', icon: MessageCircle, color: 'bg-blue-500' },
    { id: 'facebook', label: 'Facebook', icon: Globe, color: 'bg-blue-600' },
    { id: 'jiji', label: 'Jiji', icon: ShoppingBag, color: 'bg-orange-500' },
    { id: 'reddit', label: 'Reddit', icon: Globe, color: 'bg-orange-600' },
    { id: 'google', label: 'Google', icon: Search, color: 'bg-green-500' },
  ];

  const freshnessOptions = [
    { id: '24h', label: 'Last 24h', description: 'Fresh leads' },
    { id: '3d', label: 'Last 3 days', description: 'Warm leads' },
    { id: '7d', label: 'Last 7 days', description: 'Cold leads' },
  ];

  // Notify parent when filters change
  useEffect(() => {
    onFilterChange({
      sources: selectedSources,
      freshness: selectedFreshness
    });
  }, [selectedSources, selectedFreshness]);

  const toggleSource = (sourceId) => {
    setSelectedSources(prev => 
      prev.includes(sourceId)
        ? prev.filter(s => s !== sourceId)
        : [...prev, sourceId]
    );
  };

  const toggleFreshness = (freshnessId) => {
    setSelectedFreshness(prev => 
      prev.includes(freshnessId)
        ? prev.filter(f => f !== freshnessId)
        : [...prev, freshnessId]
    );
  };

  const selectAll = () => {
    setSelectedSources(sources.map(s => s.id));
    setSelectedFreshness(freshnessOptions.map(f => f.id));
  };

  const clearAll = () => {
    setSelectedSources([]);
    setSelectedFreshness([]);
  };

  const activeFiltersCount = selectedSources.length + selectedFreshness.length;
  const totalFilters = sources.length + freshnessOptions.length;

  return (
    <motion.div 
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden"
    >
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-800/80 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Filter size={18} className="text-blue-400" />
          </div>
          <div>
            <h3 className="font-bold text-white">Source Panel</h3>
            <p className="text-xs text-gray-400">
              {activeFiltersCount} of {totalFilters} filters active
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {activeFiltersCount > 0 && (
            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs font-bold rounded-full">
              {activeFiltersCount}
            </span>
          )}
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </motion.div>
        </div>
      </div>

      {/* Filter Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-gray-700"
          >
            <div className="p-4 space-y-6">
              {/* Source Filters */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                    <Globe size={14} />
                    Sources
                  </h4>
                  <span className="text-xs text-gray-500">
                    {selectedSources.length} selected
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                  {sources.map((source) => {
                    const isSelected = selectedSources.includes(source.id);
                    const Icon = source.icon;
                    return (
                      <button
                        key={source.id}
                        onClick={() => toggleSource(source.id)}
                        className={`
                          relative flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all
                          ${isSelected 
                            ? 'bg-gray-700 text-white border border-blue-500/50' 
                            : 'bg-gray-800/50 text-gray-400 border border-gray-700 hover:bg-gray-700/50'
                          }
                        `}
                      >
                        <div className={`
                          p-1 rounded 
                          ${isSelected ? source.color : 'bg-gray-700'}
                        `}>
                          <Icon size={12} className="text-white" />
                        </div>
                        <span className="flex-1 text-left">{source.label}</span>
                        {isSelected && (
                          <Check size={12} className="text-blue-400" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Divider */}
              <div className="border-t border-gray-700/50" />

              {/* Freshness Filters */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                    <Clock size={14} />
                    Freshness
                  </h4>
                  <span className="text-xs text-gray-500">
                    {selectedFreshness.length} selected
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {freshnessOptions.map((option) => {
                    const isSelected = selectedFreshness.includes(option.id);
                    return (
                      <button
                        key={option.id}
                        onClick={() => toggleFreshness(option.id)}
                        className={`
                          flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                          ${isSelected 
                            ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50' 
                            : 'bg-gray-800/50 text-gray-400 border border-gray-700 hover:bg-gray-700/50'
                          }
                        `}
                      >
                        <div className={`
                          w-4 h-4 rounded border flex items-center justify-center transition-colors
                          ${isSelected 
                            ? 'bg-blue-500 border-blue-500' 
                            : 'border-gray-500'
                          }
                        `}>
                          {isSelected && <Check size={10} className="text-white" />}
                        </div>
                        <div className="text-left">
                          <div>{option.label}</div>
                          <div className="text-xs opacity-70">{option.description}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="flex gap-2 pt-2 border-t border-gray-700/50">
                <button
                  onClick={selectAll}
                  className="flex-1 py-2 px-4 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-bold uppercase rounded-lg transition-colors"
                >
                  Select All
                </button>
                <button
                  onClick={clearAll}
                  className="flex-1 py-2 px-4 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-bold uppercase rounded-lg transition-colors"
                >
                  Clear All
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default SourceFilterPanel;
