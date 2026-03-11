// frontend/src/App.jsx
// ============================================================
// UPDATED — Wrapped with NotificationProvider
// ============================================================

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { NotificationProvider } from './context/NotificationContext';
import Layout from './components/Layout';
import Dashboard from './views/Dashboard';
import Leads from './views/Leads';
import Agents from './views/Agents';
import Settings from './views/Settings';
import LiveBuyersPage from './pages/LiveBuyersPage';
import ToastContainer from './components/ToastContainer';

const App = () => {
  return (
    <NotificationProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/leads" element={<Leads />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/live" element={<LiveBuyersPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
        
        {/* Toast notifications — renders above everything */}
        <ToastContainer />
      </Router>
    </NotificationProvider>
  );
};

export default App;