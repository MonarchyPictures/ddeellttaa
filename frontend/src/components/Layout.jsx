// frontend/src/components/Layout.jsx
// ============================================================
// UPDATED — Uses new Header with NotificationBell
// ============================================================

import React from 'react';
import Header from './Header';
import BottomNav from './BottomNav';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-black flex flex-col">
      <Header />
      <main className="flex-1">
        {children}
      </main>
      <BottomNav />
    </div>
  );
};

export default Layout;