import React, { useState, useEffect } from 'react';

function Profile({ username, isLoggedIn }) {
  const [profileData, setProfileData] = useState(null);

  useEffect(() => {
    if (!isLoggedIn) {
      setProfileData(null);
      return;
    }

    fetch(`http://localhost:5000/api/profile?username=${username}`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setProfileData(data.user);
        } else {
          console.error('프로필 정보를 불러올 수 없습니다.');
          setProfileData(null);
        }
      })
      .catch(err => {
        console.error('프로필 API 오류:', err);
        setProfileData(null);
      });
  }, [isLoggedIn, username]);

  // 수정과 삭제를 하나의 함수에서 처리하는 부분!
  const handleProfileAction = async (action) => {
    if (!profileData) return;

    if (action === 'edit') {
        const newEmail = prompt('새 이메일을 입력하세요:', profileData.email);
        const newName = prompt('새 이름을 입력하세요:', profileData.name);
        const newPassword = prompt('새 비밀번호를 입력하세요:');

        if (!newEmail || !newName || !newPassword) {
          alert('모든 정보를 입력해야 수정이 가능합니다.');
          return;
        }


      try {
// 수정 API 호출 부분
const res = await fetch('http://localhost:5000/api/update_profile', {  // 여길 update_profile 로 바꾸기!
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username,
    email: newEmail,
    name: newName,
    password: newPassword,
  }),
});

        const data = await res.json();

        if (data.success) {
          alert('프로필이 성공적으로 수정되었습니다!');
          setProfileData(prev => ({ ...profileData, email: newEmail, name: newName, }));
        } else {
          alert('프로필 수정에 실패했습니다!');
        }
      } catch (err) {
        console.error('프로필 수정 오류:', err);
        alert('오류가 발생했습니다. 다시 시도해주세요!');
      }
    } else if (action === 'delete') {
      const confirmDelete = window.confirm('정말로 회원 탈퇴를 진행하시겠습니까? 탈퇴 후에는 복구가 불가능합니다!');
      if (!confirmDelete) return;

      try {
// 삭제 API 호출 부분
const res = await fetch('http://localhost:5000/api/delete_user', {  // 여길 delete_profile 로 바꾸기!
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username }),
});

        const data = await res.json();

        if (data.success) {
          alert('회원 탈퇴가 완료되었습니다. 그동안 함께해주셔서 감사합니다! 🙏🏻');
          window.location.href = '/'; // 홈으로 리다이렉트~!
        } else {
          alert('회원 탈퇴에 실패했습니다... ㅠㅠ');
        }
      } catch (err) {
        console.error('회원 탈퇴 오류:', err);
        alert('오류가 발생했습니다. 다시 시도해주세요!');
      }
    }
  };

  if (!isLoggedIn) {
    return <p>정보를 불러올 수 없습니다. 로그인 후 이용하세요.</p>;
  }

  return (
  <>
    <h1 className="app-title">내 정보</h1>
    <div className="profile-card">
      {profileData ? (
        <>
                  <div className="profile-item">
            <span className="profile-label">아이디:</span>
            <span>{profileData.username}</span>
          </div>
          <div className="profile-item">
            <span className="profile-label">이메일:</span>
            <span>{profileData.email}</span>
          </div>
          <div className="profile-item">
            <span className="profile-label">이름:</span>
            <span>{profileData.name}</span>
          </div>
<div style={{ display: 'flex', gap: '8px' }}>
<button className="control-btn" onClick={() => handleProfileAction('edit')}
  title="회원 정보 수정"
>
  ✏️
</button>
            <button className="control-btn" onClick={() => handleProfileAction('delete')}
                title="회원 삭제"
                >
              🗑️
            </button>
          </div>
        </>
      ) : (
        <p>프로필 정보를 불러오는 중...</p>
      )}
    </div>
  </>
);
}

export default Profile;
