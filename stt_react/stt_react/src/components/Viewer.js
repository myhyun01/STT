import React, { useState, useEffect, useRef } from 'react';

function Viewer({ username, isLoggedIn, currentTitle }) {
  const [text, setText] = useState('');
  const [lastFetchedText, setLastFetchedText] = useState('');
  const [isPaused, setIsPaused] = useState(false);
  const [isStarted, setIsStarted] = useState(false);
  const [memoText, setMemoText] = useState('');
  const leftTextareaRef = useRef(null);
  const lastFetchedTextRef = useRef('');
  lastFetchedTextRef.current = lastFetchedText;

  useEffect(() => {
    if (!isStarted) return;

    const interval = setInterval(() => {
    const url = 'http://localhost:5000/api/last_transcription';


      fetch(url)
        .then(res => res.json())
        .then(data => {
          if (data.text && data.text !== lastFetchedTextRef.current) {
            setText(prev => prev + '\n' + data.text);
            setLastFetchedText(data.text);
          }
        })
        .catch(err => console.error('API 오류:', err));
    }, 1000);

    return () => clearInterval(interval);
  }, [isStarted, username]);

  useEffect(() => {
    if (leftTextareaRef.current) {
      leftTextareaRef.current.scrollTop = leftTextareaRef.current.scrollHeight;
    }
  }, [text]);

  useEffect(() => {
    if (!lastFetchedText) return;

    const fetchGPT = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: lastFetchedText,
            user_id: username,
          }),
        });
        const result = await response.json();

        if (result.memo) {
          setMemoText(prev => prev + '\n\n👉 ' + result.memo.trim());
        }
      } catch (err) {
        console.error('GPT API 오류:', err);
      }
    };

    fetchGPT();
  }, [lastFetchedText, username]);

  const fetchGPTResponse = async () => {
    if (!text) {
      alert('음성 인식 결과가 비어있습니다.');
      return;
    }

    const lines = text.split('\n').filter(line => line.trim() !== '');

    try {
      const promises = lines.map(line =>
        fetch('http://localhost:5000/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: line,
            user_id: username,
          }),
        }).then(res => res.json())
      );

      const results = await Promise.all(promises);
      const combinedMemo = results
        .map(result => (result.memo ? `👉 ${result.memo.trim()}` : ''))
        .filter(memo => memo !== '')
        .join('\n\n');

      setMemoText(combinedMemo || 'GPT 응답이 비어있습니다.');
    } catch (err) {
      console.error('GPT API 오류:', err);
      setMemoText('GPT 요청 실패');
    }
  };

const startSTT = () => {
  if (!isLoggedIn) {
    alert('로그인 후 시작할 수 있습니다.');
    return;
  }

  fetch('http://localhost:5000/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: username }),
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'started') {
        setIsStarted(true);
        setIsPaused(false);
      } else if (data.status === 'already listening') {
        alert('이미 음성 인식 중입니다.');
      }
    })
    .catch(err => console.error(err));
};

  const stopSTT = () => {
    fetch('http://localhost:5000/api/stop', { method: 'POST' })
      .then(() => {
        setIsStarted(false);
        setIsPaused(false);
      })
      .catch(err => console.error(err));
  };

  const pauseSTT = () => {
    fetch('http://localhost:5000/api/pause', { method: 'POST' })
      .then(() => setIsPaused(true))
      .catch(err => console.error(err));
  };

  const resumeSTT = () => {
    fetch('http://localhost:5000/api/resume', { method: 'POST' })
      .then(() => setIsPaused(false))
      .catch(err => console.error(err));
  };

return (
  <div className="text-box-container">
    <div className="text-area-wrapper">
      <label className="text-area-label">음성 인식 결과</label>
      <textarea
        className="text-box"
        value={text}
        readOnly
        ref={leftTextareaRef}
      />
      {/* 버튼과 저장 제목을 flex로 한 줄에 배치 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10, marginBottom: 10 }}>
        <div className="control-buttons">
          {!isStarted ? (
            <button onClick={startSTT} className="control-btn" title="시작">🎤</button>
          ) : (
            <>
              {!isPaused ? (
                <button onClick={pauseSTT} className="control-btn" title="일시정지">⏸️</button>
              ) : (
                <button onClick={resumeSTT} className="control-btn" title="다시시작">▶️</button>
              )}
              <button onClick={stopSTT} className="control-btn" title="중지">⏹️</button>
            </>
          )}
        </div>
      </div>
    </div>
    <div className="text-area-wrapper">
      <label className="text-area-label">GPT 메모</label>
      <textarea
        className="text-box"
        value={memoText}
        readOnly
        ref={leftTextareaRef}
        placeholder="GPT로부터 메모를 받아옵니다..."
      />
    </div>
  </div>
);

}

export default Viewer;