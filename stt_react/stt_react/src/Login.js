import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!username || !password) {
      alert('아이디와 비밀번호를 모두 입력하세요.');
      return;
    }

    try {
      const res = await fetch('http://localhost:5000/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (data.success) {
        alert('로그인 성공!');
        localStorage.setItem('token', data.token);
        localStorage.setItem('username', username);

        if (onLoginSuccess) {
          onLoginSuccess({ username });
        }

        navigate('/');
      } else {
        alert('로그인 실패: ' + data.message);
      }
    } catch (err) {
      console.error('로그인 오류:', err);
      alert('로그인 중 오류가 발생했습니다. 다시 시도해주세요.');
    }
  };

  return (
    <div
      style={{
            width: '100vw', 
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '20px',
        boxSizing: 'border-box',
        backgroundColor: '#f5f5f5',  // 예쁜 배경 추가 가능
      }}
    >
      {/* 전체를 감싸는 틀 */}
      <div
        style={{
          width: '100%',
          maxWidth: 400,
          backgroundColor: '#fff',
          padding: 30,
          borderRadius: 10,
          boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <h1 className="app-title" style={{ marginBottom: 30 }}>
          로그인
        </h1>
        <div
          className="login-form"
          style={{
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            gap: 15,
          }}
        >
          <input
            className="input-field"
            type="text"
            placeholder="아이디"
            value={username}
            onChange={e => setUsername(e.target.value)}
            style={{
              padding: '12px 15px',
              fontSize: 16,
              borderRadius: 5,
              border: '1px solid #ccc',
              boxSizing: 'border-box',
              width: '100%',
            }}
          />
          <input
            className="input-field"
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={{
              padding: '12px 15px',
              fontSize: 16,
              borderRadius: 5,
              border: '1px solid #ccc',
              boxSizing: 'border-box',
              width: '100%',
            }}
          />
          <button
            className="control-btn"
            onClick={handleLogin}
            title="로그인"
            style={{
              padding: '14px',
              fontSize: 18,
              fontWeight: 'bold',
              borderRadius: 5,
              border: 'none',
              backgroundColor: '#007bff',
              color: '#fff',
              cursor: 'pointer',
              width: '100%',    // 버튼 가로로 꽉 차게!
              textAlign: 'center',
            }}
          >
            로그인
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;
