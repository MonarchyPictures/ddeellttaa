import React from 'react';
import { Radar, AlertCircle, Bot, RefreshCw, ChevronRight } from 'lucide-react';

export const LeadSkeleton = () => (
  <div className="bg-white border border-gray-100 p-5 rounded-xl animate-pulse">
    <div className="flex justify-between items-start mb-3">
      <div className="h-8 w-24 bg-gray-50 rounded-lg"></div>
      <div className="h-5 w-16 bg-gray-50 rounded-full"></div>
    </div>
    <div className="h-4 w-full bg-gray-50 rounded-lg mb-2"></div>
    <div className="h-4 w-3/4 bg-gray-50 rounded-lg mb-4"></div>
    <div className="flex justify-between items-end">
      <div className="h-8 w-20 bg-gray-50 rounded-lg"></div>
      <div className="h-4 w-12 bg-gray-50 rounded-lg"></div>
    </div>
  </div>
);

export const EmptyState = ({ message, title }) => (
  <div className="flex flex-col items-center justify-center py-24 px-6 text-center bg-gray-50/50 border border-dashed border-gray-200 rounded-3xl">
    <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-8 border border-gray-200 relative">
      <Radar size={40} className="text-gray-400 animate-pulse" />
      <div className="absolute inset-0 bg-blue-500/5 rounded-full animate-ping duration-[3000ms]" />
    </div>
    <h3 className="text-2xl font-bold text-gray-900 mb-3 tracking-tight uppercase italic">{title || "Searching for Signals"}</h3>
    <p className="text-gray-500 max-w-xs text-sm font-medium leading-relaxed mb-8">
      {message || "Delta9 is scanning the network. No active buying intent detected within your current parameters yet."}
    </p>
    <button className="flex items-center gap-2 text-blue-600 font-bold text-[10px] uppercase tracking-widest group cursor-pointer">
      Broaden Search Parameters
      <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
    </button>
  </div>
);

export const ErrorState = ({ message }) => (
  <div className="flex flex-col items-center justify-center py-20 px-6 text-center bg-red-50/30 border border-red-100 rounded-3xl">
    <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-6 border border-red-200">
      <AlertCircle size={32} className="text-red-500" />
    </div>
    <h3 className="text-xl font-bold text-gray-900 mb-2 tracking-tight uppercase italic">Signal Interruption</h3>
    <p className="text-gray-500 text-sm max-w-xs font-medium leading-relaxed mb-8">
      {message || "We've lost connection to the main uplink. Our systems are working to restore the feed."}
    </p>
    <button 
      onClick={() => window.location.reload()} 
      className="flex items-center gap-2 bg-gray-900 hover:bg-gray-800 text-white font-bold text-[10px] uppercase tracking-widest px-8 py-4 rounded-xl transition-all active:scale-95 shadow-lg shadow-gray-900/10"
    >
      <RefreshCw size={14} />
      Re-establish Link
    </button>
  </div>
);

export const AgentFailedState = ({ onRetry }) => (
  <div className="flex flex-col items-center justify-center py-12 px-6 text-center bg-gray-50 border border-gray-200 rounded-3xl">
    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-6 border border-gray-200">
      <Bot size={32} className="text-gray-400" />
    </div>
    <h3 className="text-xl font-bold text-gray-900 mb-2 tracking-tight uppercase italic">Deployment Interrupted</h3>
    <p className="text-gray-500 text-sm max-w-xs font-medium leading-relaxed mb-8">
      The agent couldn't be initialized at this time. Please check your configuration and try again.
    </p>
    <div className="flex flex-col gap-4 w-full">
      <button 
        onClick={onRetry}
        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-[10px] uppercase tracking-widest py-4 rounded-xl transition-all active:scale-95 shadow-lg shadow-blue-600/20"
      >
        Review Settings
      </button>
      <button 
        className="w-full text-gray-500 font-bold text-[10px] uppercase tracking-widest py-2 hover:text-gray-900 transition-colors"
        onClick={() => window.location.reload()}
      >
        Return to Dashboard
      </button>
    </div>
  </div>
);
