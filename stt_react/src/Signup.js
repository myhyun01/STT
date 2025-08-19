import React, { useState } from 'react';

function Signup() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');  
  const [name, setName] = useState('');     

  const handleSignup = async () => {
    if (!username || !password || !email || !name) {
      alert('모든 항목을 입력해주세요.');
      return;
    }

    try {
      const res = await fetch('http://localhost:5000/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, email, name }),
      });

      const data = await res.json();

      if (data.success) {
        alert('회원가입 성공!');
        window.location.href = '/login';
      } else {
        alert('회원가입 실패: ' + data.message);
      }
    } catch (err) {
      console.error('회원가입 오류:', err);
      alert('회원가입 중 오류가 발생했습니다. 다시 시도해주세요.');
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '20px',
        boxSizing: 'border-box',
        backgroundColor: '#f5f5f5',
      }}
    >
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
        <h1 style={{ marginBottom: 30, color: '#3F51B5'}}>회원가입</h1>
        <div
          style={{
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            gap: 15,
          }}
        >
          <input
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
          <input
            type="email"
            placeholder="이메일"
            value={email}
            onChange={e => setEmail(e.target.value)}
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
            type="text"
            placeholder="이름"
            value={name}
            onChange={e => setName(e.target.value)}
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
            onClick={handleSignup}
            style={{
              padding: '14px',
              fontSize: 18,
              fontWeight: 'bold',
              borderRadius: 5,
              border: 'none',
              backgroundColor: '#3F51B5',
              color: '#fff',
              cursor: 'pointer',
              width: '100%',
              textAlign: 'center',
            }}
          >
            회원가입
          </button>
        </div>
      </div>
    </div>
  );
}

export default Signup;
