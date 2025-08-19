import React, { useState, useEffect, useRef } from 'react';

export default function Sidebar({ onNavigate }) {
  return (
    <nav className="sidebar">
      <button onClick={() => onNavigate('/')} title="음성 인식 뷰어" className="viewer-button hover-effect-button">🎤</button>
      <button onClick={() => onNavigate('/search')} title="검색" className="viewer-button hover-effect-button">🔍</button>
      <button onClick={() => onNavigate('/original')} title="원문" className="viewer-button hover-effect-button">📄</button>
      <div className="settings-button-wrapper">
        <button onClick={() => onNavigate('/settings')} title="환경설정" className="viewer-button hover-effect-button">⚙️</button>
      </div>
    </nav>
  );
}
