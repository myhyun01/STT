import React, { useState, useEffect, useRef } from 'react';

export default function Header({ isLoggedIn, username, onLogout, onNavigate }) {
  return (
    <header className="top-header">
      <div
        className="header-title hover-effect-button"
        onClick={() => onNavigate('/')}
        title="홈으로 이동"
      >
        LVTT
      </div>
      <div className="top-right-buttons">
        <button className="header-icon-button hover-effect-button" onClick={() => onNavigate('/profile')} title="내 정보">👤</button>
        {!isLoggedIn ? (
          <>
            <button className="auth-button" onClick={() => onNavigate('/login')}>로그인</button>
            <button className="auth-button" onClick={() => onNavigate('/signup')}>회원가입</button>
          </>
        ) : (
          <button className="auth-button" onClick={() => { onLogout(); onNavigate('/'); }}>로그아웃</button>
        )}
      </div>
    </header>
  );
}
