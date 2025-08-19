import React, { useEffect, useState } from 'react';

function Result({ username }) {
  const [fileList, setFileList] = useState([]);
  const [error, setError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [sentences, setSentences] = useState([]);
  const [loadingSentences, setLoadingSentences] = useState(false);

  useEffect(() => {
    if (!username) {
      setError('로그인이 필요합니다.');
      setFileList([]);
      return;
    }

    fetch(`http://localhost:5000/api/text_files?user_id=${encodeURIComponent(username)}`)
      .then(res => {
        if (!res.ok) throw new Error('파일 목록을 불러오는 데 실패했습니다.');
        return res.json();
      })
      .then(data => {
        setFileList(data.titles || []);
        setError(null);
      })
      .catch(err => {
        setError(err.message);
        setFileList([]);
      });
  }, [username]);

  // 파일 클릭 시 문장 + 문장 뜻 같이 불러오기
  const handleFileClick = (fileName) => {
    setSelectedFile(fileName);
    setLoadingSentences(true);

    fetch(`http://localhost:5000/api/text_file_sentences_with_gpt?user_id=${encodeURIComponent(username)}&original_title=${encodeURIComponent(fileName)}`)
      .then(res => {
        if (!res.ok) throw new Error('문장 목록을 불러오는 데 실패했습니다.');
        return res.json();
      })
      .then(data => {
        if (data.success) {
          // sentence_mean 포함된 문장 배열로 상태 세팅
          setSentences(data.sentences);
          setError(null);
        } else {
          setSentences([]);
          setError(data.message || '문장 목록을 불러오지 못했습니다.');
        }
      })
      .catch(err => {
        setSentences([]);
        setError(err.message);
      })
      .finally(() => setLoadingSentences(false));
  };

  // 파일 삭제 함수
  const handleDeleteFile = (fileName) => {
    if (!window.confirm(`정말 "${fileName}" 파일을 삭제하시겠습니까?`)) return;

    fetch('http://localhost:5000/api/delete_original', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: username,
        title: fileName
      })
    })
      .then(res => {
        if (!res.ok) throw new Error('파일 삭제에 실패했습니다.');
        return res.json();
      })
      .then(data => {
        if (data.success) {
          alert('파일이 삭제되었습니다.');
          setFileList(prevList => prevList.filter(f => f !== fileName));
          if (selectedFile === fileName) {
            setSelectedFile(null);
            setSentences([]);
          }
        } else {
          alert(data.message || '파일 삭제 실패');
        }
      })
      .catch(err => {
        alert(err.message);
      });
  };

  return (
    <div style={{ display: 'flex' }}>
      {/* 왼쪽 영역: 파일 목록 */}
      <div style={{ width: '30%', color: '#3F51B5', marginRight: '20px', backgroundColor: '#f0f0f0', padding: '10px', borderRadius: '8px' }}>
        <h2>저장된 파일 목록(해석)</h2>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        {fileList.length === 0 && !error ? (
          <p>저장된 파일이 없습니다.</p>
        ) : (
          <ul style={{ listStyleType: 'none', padding: 0 }}>
            {fileList.map((fileName, idx) => (
              <li
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '10px',
                  padding: '8px',
                  backgroundColor: selectedFile === fileName ? '#d1cdee' : '#d1cdee',
                  border: '1px solid #ccc',
                  borderRadius: '5px'
                }}
              >
                <span
                  style={{
                    cursor: 'pointer',
                    fontWeight: selectedFile === fileName ? 'bold' : 'normal',
                    color: '#3F51B5'
                  }}
                  onClick={() => handleFileClick(fileName)}
                >
                  {fileName}
                </span>
                <button
                  style={{
                    backgroundColor: '#f44336',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    cursor: 'pointer'
                  }}
                  onClick={() => handleDeleteFile(fileName)}
                >
                  삭제
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 오른쪽 영역: 선택된 파일의 문장 및 뜻 */}
      <div style={{ width: '70%',height:'100%', color: '#3F51B5', backgroundColor: '#d1cdee', padding: '30px', borderRadius: '8px' }}>
        {selectedFile ? (
          <div>
            <h2>{selectedFile} 의 문장 목록</h2>
            {loadingSentences ? (
              <p>문장 불러오는 중...</p>
            ) : sentences.length === 0 ? (
              <p>문장이 없습니다.</p>
            ) : (
              <ol>
                {sentences.map(({ sentence_number, sentence_content, sentence_mean }) => (
                  <li key={sentence_number} style={{ marginBottom: '12px' }}>
                    <div><strong>{sentence_content}</strong></div>
                    {sentence_mean && (
                      <div style={{ color: '#555', marginTop: '4px', fontStyle: 'italic' }}>
                        뜻: {sentence_mean}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        ) : (
          <p>파일을 선택하면 문장이 여기에 표시됩니다.</p>
        )}
      </div>
    </div>
  );
}

export default Result;
