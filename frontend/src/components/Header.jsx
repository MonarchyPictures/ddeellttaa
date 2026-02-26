import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Activity } from 'lucide-react';
import NotificationBell from './NotificationBell';
import { useNotifications } from '../context/NotificationContext';

const Header = () => {
  const location = useLocation();
  const { isConnected } = useNotifications();

  return (
    <header className="fixed top-0 left-0 right-0 z-40 bg-black/80 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-400 flex items-center justify-center">
            <Activity className="w-4 h-4 text-black" />
          </div>
          <span className="text-white font-bold text-lg">Delta 9</span>
          
          {/* Live indicator */}
          {isConnected && (
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20">
              <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
              <span className="text-green-400 text-[10px] font-medium">LIVE</span>
            </div>
          )}
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-1">
          {[
            { path: '/', label: 'Dashboard' },
            { path: '/leads', label: 'Leads' },
            { path: '/agents', label: 'Agents' },
            { path: '/settings', label: 'Settings' },
          ].map(({ path, label }) => (
            <Link
              key={path}
              to={path}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                location.pathname === path
                  ? 'bg-white/10 text-white'
                  : 'text-white/40 hover:text-white/60 hover:bg-white/5'
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* Right Side */}
        <div className="flex items-center gap-3">
          <NotificationBell />
        </div>
      </div>
    </header>
  );
};

export default Header;
