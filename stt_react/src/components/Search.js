import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

function Search({ username, isLoggedIn }) {
  const [textFiles, setTextFiles] = React.useState([]);
  const [filteredFiles, setFilteredFiles] = React.useState([]);
  const [searchTerm, setSearchTerm] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const OPENAI_API_KEY = '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';

  React.useEffect(() => {
    if (!isLoggedIn) {
      setTextFiles([]);
      setFilteredFiles([]);
      return;
    }

    setLoading(true);
    fetch(`http://localhost:5000/api/text_files?user_id=${username}`)
      .then(res => {
        if (!res.ok) throw new Error('텍스트 파일 목록을 불러오는데 실패했습니다.');
        return res.json();
      })
      .then(data => {
        const files = data.files || [];
        setTextFiles(files);
        setFilteredFiles(files);
      })
      .catch(err => {
        console.error(err);
        setTextFiles([]);
        setFilteredFiles([]);
      })
      .finally(() => setLoading(false));
  }, [username, isLoggedIn]);

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post(
        'https://api.openai.com/v1/chat/completions',
        {
          model: 'gpt-3.5-turbo',
          messages: [{ role: 'user', content: `"${searchTerm}"에 대해 알려줘.` }],
        },
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${OPENAI_API_KEY}`,
          },
        }
      );

      const gptMessage = response.data.choices[0].message.content.trim();
      setFilteredFiles(gptMessage.split('\n').filter(line => line.trim() !== ''));
    } catch (error) {
      console.error('GPT 요청 실패:', error);
      setFilteredFiles(['검색 중 오류가 발생했습니다.']);
    } finally {
      setLoading(false);
    }
  };

  if (!isLoggedIn) {
    return <p style={{ textAlign: 'center', marginTop: '40px' }}>로그인 후 이용 가능합니다.</p>;
  }

  if (loading) {
    return <p style={{ textAlign: 'center', marginTop: '40px' }}>로딩 중...</p>;
  }

  return (
    <div
      style={{
        maxWidth: '900px',
        margin: '40px auto',
        padding: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        borderRadius: '8px',
        backgroundColor: '#fafafa',
        display: 'flex',
        flexDirection: 'column',
        height: '80vh',
      }}
    >
      <h1 style={{ textAlign: 'center', marginBottom: '30px', color: '#3F51B5' }}>검색</h1>

      <div style={{ display: 'flex', marginBottom: '20px', gap: '10px' }}>
        <input
          type="text"
          placeholder="검색어를 입력하세요"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            flex: 1,
            padding: '12px 15px',
            fontSize: '1.1rem',
            borderRadius: '6px',
            border: '2px solid #3F51B5',
            outline: 'none',
            boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.1)',
          }}
          onKeyDown={e => { if (e.key === 'Enter') handleSearch(); }}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: '12px 25px',
            fontSize: '1.1rem',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: '#3F51B5',
            color: 'white',
            cursor: 'pointer',
            transition: 'background-color 0.3s',
          }}
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#303F9F')}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = '#3F51B5')}
        >
          검색
        </button>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          border: '2px solid #3F51B5',
          borderRadius: '6px',
          padding: '15px',
          backgroundColor: 'white',
          fontSize: '1rem',
          color: '#444',
          lineHeight: '1.5',
        }}
      >
        {filteredFiles.length === 0 ? (
          <p style={{ textAlign: 'center', color: '#888' }}>검색 결과가 없습니다.</p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {filteredFiles.map((file, idx) => (
              <li
                key={idx}
                style={{
                  padding: '10px 15px',
                  marginBottom: '10px',
                  backgroundColor: '#E3F2FD', // 연한 파란색 배경
                  borderRadius: '6px',
                  color: '#333',
                  borderBottom: idx !== filteredFiles.length - 1 ? '1px solid #eee' : 'none',
                }}
              >
                {file}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default Search;
