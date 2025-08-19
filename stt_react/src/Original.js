import React, { useEffect, useState } from 'react';

function Original({ username }) {
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
        setError(null);  // 에러 초기화
      })
      .catch(err => {
        setError(err.message);
        setFileList([]);
      });
  }, [username]);

  // 파일 클릭 시 문장 불러오기
  const handleFileClick = (fileName) => {
    setSelectedFile(fileName);
    setLoadingSentences(true);
    fetch(`http://localhost:5000/api/text_file_sentences?user_id=${encodeURIComponent(username)}&original_title=${encodeURIComponent(fileName)}`)
      .then(res => {
        if (!res.ok) throw new Error('문장 목록을 불러오는 데 실패했습니다.');
        return res.json();
      })
      .then(data => {
        if (data.success) {
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

  return (
<div style={{ display: 'flex' }}>
  {/* 왼쪽 영역: 파일 목록 */}
  <div style={{ width: '30%', color: '#3F51B5', marginRight: '20px', backgroundColor: '#f0f0f0', padding: '10px', borderRadius: '8px' }}>
    <h2>저장된 파일 목록</h2>
    {error && <p style={{ color: 'red' }}>{error}</p>}
    {fileList.length === 0 && !error ? (
      <p>저장된 파일이 없습니다.</p>
    ) : (
      <ul style={{ listStyleType: 'none', padding: 0 }}>
        {fileList.map((fileName, idx) => (
          <li
  key={idx}
  style={{
    cursor: 'pointer',
    fontWeight: selectedFile === fileName ? 'bold' : 'normal',
    color: '#3F51B5',  // ✅ 글자 색 고정
    marginBottom: '10px',
    padding: '8px',
    backgroundColor: selectedFile === fileName ? '#d1cdee' : '#d1cdee',
    border: '1px solid #ccc',
    borderRadius: '5px'
  }}
  onClick={() => handleFileClick(fileName)}
>
  {fileName}
</li>


        ))}
      </ul>
    )}
  </div>

  {/* 오른쪽 영역: 선택된 파일의 문장 */}
  <div style={{ width: '70%', color: '#3F51B5', backgroundColor: '#d1cdee', padding: '10px', borderRadius: '8px'}}>
    {selectedFile ? (
      <div>
        <h2>{selectedFile} 의 문장 목록</h2>
        {loadingSentences ? (
          <p>문장 불러오는 중...</p>
        ) : sentences.length === 0 ? (
          <p>문장이 없습니다.</p>
        ) : (
          <ol>
            {sentences.map(sentence => (
              <li key={sentence.sentence_number}>{sentence.sentence_content}</li>
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




export default Original;
