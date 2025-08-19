import React, { useState } from 'react';

export default function Sidebar({ onNavigate }) {
  const [activePage, setActivePage] = useState('/');

  const handleNavigate = (path) => {
    setActivePage(path);
    onNavigate(path);
  };

  return (
    <nav className="sidebar">
      <div
        className={`sidebar-item ${activePage === '/' ? 'active' : ''}`}
        onClick={() => handleNavigate('/')}
      >
        <span className="sidebar-icon">🎤</span>
      </div>

      <div
        className={`sidebar-item ${activePage === '/search' ? 'active' : ''}`}
        onClick={() => handleNavigate('/search')}
      >
        <span className="sidebar-icon">🔍</span>
      </div>

      <div
        className={`sidebar-item ${activePage === '/original' ? 'active' : ''}`}
        onClick={() => handleNavigate('/original')}
      >
        <span className="sidebar-icon">📄</span>
      </div>

      <div
        className={`sidebar-item ${activePage === '/result' ? 'active' : ''}`}
        onClick={() => handleNavigate('/result')}
      >
        <span className="sidebar-icon">📖</span>
      </div>
    </nav>
  );
}
