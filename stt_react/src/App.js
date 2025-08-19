import React, { useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import Sidebar from './components/SideBar';
import Header from './components/Header';
import Viewer from './components/Viewer';
import Search from './components/Search';
import Profile from './components/Profile';
import Settings from './components/Settings';
import Login from './Login';
import Signup from './Signup';
import Original from './Original';
import './App.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState(null);

  const navigate = useNavigate();

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUsername(null);
  };

  const handleLoginSuccess = (user) => {
    setIsLoggedIn(true);
    setUsername(user.username);
    navigate('/');
  };

  return (
    <div className="App">
      <Sidebar onNavigate={navigate} />
      <Header
        isLoggedIn={isLoggedIn}
        username={username}
        onLogout={handleLogout}
        onNavigate={navigate}
      />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Viewer username={username} isLoggedIn={isLoggedIn} />} />
          <Route path="/login" element={<Login onLoginSuccess={handleLoginSuccess} />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/original" element={<Original username={username} />} />
          <Route path="/search" element={<Search username={username} isLoggedIn={isLoggedIn} />} />
          <Route path="/profile" element={<Profile username={username} isLoggedIn={isLoggedIn} />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
