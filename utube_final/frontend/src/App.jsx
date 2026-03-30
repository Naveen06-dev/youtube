import { useState, useEffect } from 'react';
import './App.css';
import LoginPage from './LoginPage';

const API_BASE = import.meta.env.VITE_API_BASE || 'https://my-youtube-backend-0uzu.onrender.com';
// Simple fixed user id for personalization
const USER_ID = "demo_user_123";

const getChannelAvatar = (name, logoUrl = null) => {
  if (logoUrl) return logoUrl;
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name || 'User')}&background=random&color=fff&size=64`;
};

function App() {
  const [currentVideo, setCurrentVideo] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [allVideos, setAllVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  const activeUserId = currentUser ? String(currentUser.id) : USER_ID;

  // Initial Load
  const [view, setView] = useState('home'); // 'home', 'watch', 'history', 'playlist'
  const [history, setHistory] = useState([]);

  const fetchHistory = () => {
    fetch(`${API_BASE}/history/${activeUserId}`)
      .then(res => res.json())
      .then(data => setHistory(data))
      .catch(err => console.error("Failed to load history", err));
  };




  // Initial Load
  useEffect(() => {
    if (!isLoggedIn) {
      setLoading(false);
      return;
    }

    setLoading(true);
    const startTime = Date.now();
    const MIN_LOADING_TIME = 1000;

    fetch(`${API_BASE}/videos?t=${Date.now()}&user_id=${activeUserId}`)
      .then(res => res.json())
      .then(data => {
        setAllVideos(data);
        const elapsed = Date.now() - startTime;
        const remainingTime = Math.max(0, MIN_LOADING_TIME - elapsed);
        setTimeout(() => setLoading(false), remainingTime);
      })
      .catch(err => {
        console.error("Failed to fetch videos:", err);
        setLoading(false);
      });
  }, [isLoggedIn, activeUserId]);

  const loadVideo = async (video) => {
    setRecommendations([]); // Clear old recommendations first
    setCurrentVideo(video);
    setView('watch');

    // 1. Log Interaction (Real-time learning)
    try {
      await fetch(`${API_BASE}/interaction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: activeUserId,
          video_id: video.id,
          action: "click"
        })
      });
    } catch (e) {
      console.warn("Analytics failed", e);
    }

    // 2. Fetch Personalized Recommendations
    try {
      const res = await fetch(`${API_BASE}/recommend/${video.id}?user_id=${activeUserId}`);
      const recs = await res.json();
      setRecommendations(recs);
    } catch (err) {
      console.error("Failed to fetch recommendations:", err);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /* SEARCH SUGGESTIONS LOGIC */
  const [searchQuery, setSearchQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  /* VOICE SEARCH LOGIC */
  const [isListening, setIsListening] = useState(false);

  const startVoiceSearch = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser doesn't support Voice Search. Please try a modern browser like Chrome or Edge.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsListening(true);
    
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setSearchQuery(transcript);
      performSearch(transcript);
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      setIsListening(false);
    };

    recognition.onend = () => setIsListening(false);

    recognition.start();
  };


  // Debounce search input to fetch suggestions
  useEffect(() => {
    // If empty, clear everything
    if (!searchQuery) {
      setSuggestions([]);
      setShowSuggestions(false);
      setIsSearching(false);
      return;
    }

    setIsSearching(true); // User is typing/waiting

    const delayDebounceFn = setTimeout(() => {
      if (searchQuery.length > 1) {
        fetch(`${API_BASE}/suggestions?q=${searchQuery}`)
          .then(res => res.json())
          .then(data => {
            setSuggestions(data); // Suggestions are now just {id, title}
            setShowSuggestions(true);
            setIsSearching(false);
          })
          .catch(err => {
            console.error("Suggestion fetch failed", err);
            setIsSearching(false);
          });
      } else {
        setSuggestions([]);
        setShowSuggestions(false);
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  const performSearch = (query, switchToHome = true) => {
    // Hide dropdown
    setShowSuggestions(false);

    fetch(`${API_BASE}/videos?q=${query}&user_id=${activeUserId}`)
      .then(res => res.json())
      .then(data => {
        setAllVideos(data); // Update the grid
        if (switchToHome) {
          setView('home');    // Show the grid with results only if explicit search
        }
      })
      .catch(err => {
        console.error("Search failed:", err);
      });
  }

  const handleSearch = (e) => {
    if (e.key === 'Enter') {
      performSearch(searchQuery);
    }
  };

  /* CATEGORY FILTER LOGIC */




  // ============ SOCIAL FEATURES STATE ============
  const [likes, setLikes] = useState(0);
  const [dislikes, setDislikes] = useState(0);
  const [userLikeAction, setUserLikeAction] = useState(null); // 'like', 'dislike', or null
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subCount, setSubCount] = useState(0);
  const [comments, setComments] = useState([]);
  const [commentText, setCommentText] = useState('');

  // Share State
  const [showShareModal, setShowShareModal] = useState(false);

  // Playlist State
  const [userPlaylists, setUserPlaylists] = useState([]);
  const [showPlaylistModal, setShowPlaylistModal] = useState(false);
  const [videoToSave, setVideoToSave] = useState(null);
  const [newPlaylistName, setNewPlaylistName] = useState("");
  const [selectedPlaylistView, setSelectedPlaylistView] = useState(null);

  const fetchPlaylists = () => {
    fetch(`${API_BASE}/playlists/${activeUserId}`)
      .then(res => res.json())
      .then(data => setUserPlaylists(data))
      .catch(err => console.error("Failed to load playlists", err));
  };

  useEffect(() => {
    if (isLoggedIn) {
      fetchPlaylists();
    }
  }, [isLoggedIn, activeUserId]);

  const handleAddToPlaylist = (playlistName, videoId) => {
    fetch(`${API_BASE}/playlists/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: activeUserId,
        playlist_name: playlistName,
        video_id: videoId
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          alert(`Added to ${playlistName}`);
          fetchPlaylists();
        } else {
          alert(`Video is already in ${playlistName}`);
        }
        setShowPlaylistModal(false);
      });
  };

  const loadPlaylistVideos = (playlistName) => {
    setSelectedPlaylistView(playlistName);
    setView('playlist');
    fetch(`${API_BASE}/playlists/${activeUserId}/${playlistName}`)
      .then(res => res.json())
      .then(data => setAllVideos(data))
      .catch(err => console.error("Failed to load playlist videos", err));
  };


  // UI State
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);

  // Clear History Handler
  const clearHistory = async () => {
    try {
      await fetch(`${API_BASE}/history/${activeUserId}`, { method: 'DELETE' });
      setHistory([]); // Clear local state
      setAllVideos([]); // Ensure no videos are displayed on Home
      setRecommendations([]); // Clear any recommendations
      setUserPlaylists([]); // Clear playlists in local state
      setView('home'); // Switch to home view to show empty state
      fetchPlaylists(); // Refresh from server to get default empty state
      alert("History, Recommendations, and Playlists have been reset.");
      setShowProfileMenu(false);
    } catch (err) {
      console.error("Failed to clear history", err);
    }
  };

  // Fetch social data when video changes
  useEffect(() => {
    if (currentVideo) {
      // Fetch likes
      fetch(`${API_BASE}/likes/${currentVideo.id}?user_id=${activeUserId}`)
        .then(res => res.json())
        .then(data => {
          setLikes(data.likes);
          setDislikes(data.dislikes);
          setUserLikeAction(data.user_action);
        })
        .catch(console.error);

      // Fetch subscription status
      const channelId = currentVideo.channelTitle || currentVideo.id;
      fetch(`${API_BASE}/subscribed/${channelId}?user_id=${activeUserId}`)
        .then(res => res.json())
        .then(data => {
          setIsSubscribed(data.is_subscribed);
          setSubCount(data.subscriber_count);
        })
        .catch(console.error);

      // Fetch comments
      fetch(`${API_BASE}/comments/${currentVideo.id}`)
        .then(res => res.json())
        .then(data => setComments(data.comments || []))
        .catch(console.error);


    }
  }, [currentVideo]);

  // Like/Dislike Handler
  const handleLike = async (isLike) => {
    try {
      const res = await fetch(`${API_BASE}/like`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: activeUserId,
          video_id: currentVideo.id,
          is_like: isLike
        })
      });
      const data = await res.json();
      setLikes(data.likes);
      setDislikes(data.dislikes);
      setUserLikeAction(data.user_action);
    } catch (err) {
      console.error("Like failed:", err);
    }
  };

  // Subscribe Handler
  const handleSubscribe = async () => {
    const channelId = currentVideo.channelTitle || currentVideo.id;
    try {
      const res = await fetch(`${API_BASE}/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: activeUserId,
          channel_id: channelId
        })
      });
      const data = await res.json();
      setIsSubscribed(data.action === 'subscribed');
      setSubCount(data.subscriber_count);
    } catch (err) {
      console.error("Subscribe failed:", err);
    }
  };



  // Add Comment Handler
  const handleAddComment = async () => {
    if (!commentText.trim()) return;

    try {
      const res = await fetch(`${API_BASE}/comment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: activeUserId,
          video_id: currentVideo.id,
          text: commentText
        })
      });
      const data = await res.json();
      setComments([data.comment, ...comments]);
      setCommentText('');
    } catch (err) {
      console.error("Comment failed:", err);
    }
  };

  if (loading) {
    return (
      <div className="loading-spinner">
        <div className="loader"></div>
      </div>
    );
  }

  const handleLogin = (data) => {
    setIsLoggedIn(true);
    if (data && data.email) {
      setCurrentUser(data);
    } else if (data && data.user) {
      setCurrentUser(data.user);
    } else {
      // Fallback
      setCurrentUser({
        id: "admin_user",
        name: "Admin",
        email: "admin@cntube.com",
        avatar: "https://ui-avatars.com/api/?name=Admin&background=0D8ABC&color=fff"
      });
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setCurrentUser(null);
    setShowProfileMenu(false);
  };

  if (!isLoggedIn) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <div className="app-container">
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-left">
          <div className="menu-icon" onClick={() => setShowSidebar(!showSidebar)}>
            ☰
          </div>
          <div className="logo" onClick={() => {
            setView('home');
            setSearchQuery("");
            // Fetch Home feed - Backend will return empty if no history (Search-first requirement)
            fetch(`${API_BASE}/videos?user_id=${activeUserId}`).then(r => r.json()).then(setAllVideos);
          }} style={{ cursor: 'pointer' }}>
            <span style={{ color: '#e32020ff' }}>N </span><span className="logo-accent">Tube</span>
          </div>
        </div>

        <div className="search-container-wrapper" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className={`search-bar ${showSuggestions ? 'active' : ''}`} style={{ margin: 0 }}>
            {/* Actionable Search Icon */}
            <span
              className="search-icon-left clickable"
              onClick={() => performSearch(searchQuery)}
              title="Search"
            >
              {isSearching ? <div className="spinner-small"></div> : '🔍'}
            </span>
            <input
              type="text"
              className="search-input"
              placeholder="Search specific topics..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearch}
              onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true); }}
              // Delayed hide to allow clicking suggestion
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            />
            {/* Clear Button */}
            {searchQuery && (
              <span
                className="search-clear-btn"
                onClick={() => {
                  setSearchQuery("");
                  performSearch("", true); // Reset to all videos
                }}
              >
                ×
              </span>
            )}
          </div>
          
          <button
            className="mic-btn"
            onClick={startVoiceSearch}
            title={isListening ? "Listening..." : "Search with your voice"}
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              border: 'none',
              background: isListening ? '#cc0000' : '#222',
              color: '#fff',
              fontSize: '1.2rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            🎙️
          </button>
          

          {/* Suggestions Dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div className="search-suggestions">
              {suggestions.map((video) => (
                <div
                  key={video.id}
                  className="suggestion-item"
                  onClick={() => {
                    setSearchQuery(video.title);

                    // Fetch full video details using the ID from suggestion
                    fetch(`${API_BASE}/videos/${video.id}`)
                      .then(r => r.json())
                      .then(fullVideo => {
                        loadVideo(fullVideo);
                        performSearch(video.title, false);
                      });
                  }}
                >
                  <span className="suggestion-icon">↗</span>
                  <span>{video.title}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="navbar-actions" style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          {/* History Button */}
          <div
            className="icon-btn clickable"
            onClick={() => {
              setView('history');
              fetchHistory();
            }}
            title="Watch History"
            style={{ fontSize: '1.2rem', padding: '8px' }}
          >
            🕒
          </div>




          <div className="user-profile-container" style={{ position: 'relative' }}>
            <div
              className="user-icon clickable"
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              style={{ width: 35, height: 35, borderRadius: '50%', background: '#555', cursor: 'pointer', overflow: 'hidden' }}
            >
              {/* Profile Initials/Icon */}
              <img
                src={currentUser?.avatar || "https://ui-avatars.com/api/?name=User&background=0D8ABC&color=fff"}
                alt="Profile"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>

            {/* Profile Dropdown */}
            {showProfileMenu && (
              <div className="profile-menu">
                <div className="profile-header">
                  <div className="profile-name">{currentUser.name || 'User'}</div>
                  <div className="profile-email">{currentUser.email || 'user@example.com'}</div>
                </div>
                <div className="profile-divider"></div>
                <button className="profile-item" onClick={clearHistory}>
                  🗑️ Clear History & Reset
                </button>
                <div className="profile-item">⚙️ Settings</div>
                <button className="profile-item" onClick={handleLogout} style={{ color: '#ff4d4f' }}>
                  🚪 Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      <div className="app-layout">
        {showSidebar && (
          <aside className="sidebar">
            <div className="sidebar-section">
              <div
                className={`sidebar-item ${view === 'home' ? 'active' : ''}`}
                onClick={() => {
                  setView('home');
                  setSearchQuery("");
                  fetch(`${API_BASE}/videos?user_id=${activeUserId}`).then(r => r.json()).then(setAllVideos);
                }}
              >
                🏠 Home
              </div>
              <div
                className={`sidebar-item ${view === 'history' ? 'active' : ''}`}
                onClick={() => {
                  setView('history');
                  fetchHistory();
                }}
              >
                🕒 History
              </div>
            </div>

            <div className="sidebar-divider"></div>

            <div className="sidebar-section">
              <h3 className="sidebar-title">Playlists</h3>
              <div
                className={`sidebar-item ${selectedPlaylistView === 'Watch Later' && view === 'playlist' ? 'active' : ''}`}
                onClick={() => loadPlaylistVideos("Watch Later")}
              >
                🕒 Watch Later
              </div>
              {userPlaylists.filter(p => p.name !== "Watch Later").map(pl => (
                <div
                  key={pl.name}
                  className={`sidebar-item ${selectedPlaylistView === pl.name && view === 'playlist' ? 'active' : ''}`}
                  onClick={() => loadPlaylistVideos(pl.name)}
                >
                  📑 {pl.name}
                </div>
              ))}
            </div>
          </aside>
        )}
        <main className={`main-content ${view === 'watch' ? 'watch-view-layout' : ''}`}>
          {view === 'home' ? (
            /* HOME DASHBOARD GRID */
            <>
              <div className="video-grid">
                {allVideos.length > 0 ? (
                  allVideos.map(video => (
                    <div key={video.id} className="video-card-home" onClick={() => loadVideo(video)}>
                      <div className="thumbnail-container" style={{ position: 'relative' }}>
                        <img src={video.thumbnail} alt={video.title} className="video-thumb-home" />
                        {video.duration && <div className="video-duration">{video.duration}</div>}
                        <button
                          className="add-to-playlist-overlay"
                          onClick={(e) => {
                            e.stopPropagation();
                            setVideoToSave(video);
                            setShowPlaylistModal(true);
                          }}
                          title="Save to playlist"
                        >
                          📑+
                        </button>
                      </div>
                      <div className="video-info-home">
                        <img
                          className="video-avatar"
                          src={getChannelAvatar(video.channelTitle, video.channelThumbnail)}
                          alt=""
                          style={{ borderRadius: '50%', objectFit: 'cover' }}
                        />
                        <div className="video-text">
                          <div className="video-title-home">{video.title}</div>
                          <div className="video-meta-home">{video.channelTitle || 'Unknown'}</div>
                          <div className="video-meta-home">{video.category} • 2M views • 👍 {video.likes ?? 0}</div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div
                    className="empty-search-state"
                    style={{
                      gridColumn: '1 / -1',
                      textAlign: 'center',
                      padding: '4rem',
                      color: '#888'
                    }}
                  >
                    <h2 style={{ fontSize: '2rem', marginBottom: '1rem' }}>🔍 Go and Search</h2>
                    <p style={{ fontSize: '1.2rem', marginBottom: '1.5rem' }}>Ready to watch something amazing? Start by searching or picking a category!</p>
                    <button
                      onClick={() => document.querySelector('.search-input')?.focus()}
                      style={{
                        padding: '12px 32px',
                        fontSize: '1rem',
                        borderRadius: '24px',
                        border: 'none',
                        background: '#fff',
                        color: '#000',
                        fontWeight: '600',
                        cursor: 'pointer'
                      }}
                    >
                      Start Searching
                    </button>
                  </div>
                )}
              </div>

              {allVideos.length > 0 && (
                <div
                  className="load-more-container"
                  style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}
                >
                  <button
                    className="load-more-btn"
                    onClick={() => {
                      const btn = document.querySelector('.load-more-btn');
                      if (btn) {
                        btn.innerText = 'Loading new videos...';
                        btn.disabled = true;
                        btn.style.opacity = '0.7';
                        btn.style.cursor = 'wait';
                      }

                      fetch(`${API_BASE}/sync`)
                        .then(res => res.json())
                        .then(() => {
                          return fetch(`${API_BASE}/videos?user_id=${activeUserId}`);
                        })
                        .then(res => res.json())
                        .then(data => {
                          setAllVideos(data);
                          if (btn) {
                            btn.innerText = 'Load More Videos';
                            btn.disabled = false;
                            btn.style.opacity = '1';
                            btn.style.cursor = 'pointer';
                          }
                        })
                        .catch(err => {
                          console.error('Failed to load more', err);
                          if (btn) {
                            btn.innerText = 'Try Again';
                            btn.disabled = false;
                            btn.style.opacity = '1';
                          }
                        });
                    }}
                    style={{
                      padding: '12px 32px',
                      fontSize: '1rem',
                      fontWeight: '600',
                      borderRadius: '24px',
                      border: '1px solid #333',
                      background: '#1f1f1f',
                      color: '#fff',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                    onMouseOver={e => (e.target.style.background = '#333')}
                    onMouseOut={e => (e.target.style.background = '#1f1f1f')}
                  >
                    Load More Videos
                  </button>
                </div>
              )}
            </>
          ) : view === 'playlist' ? (
            /* PLAYLIST VIEW */
            <>
              <div className="playlist-page-header" style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📑 {selectedPlaylistView}</h1>
                <p style={{ color: '#aaa' }}>{allVideos.length} videos</p>
              </div>
              <div className="video-grid">
                {allVideos.length > 0 ? (
                  allVideos.map(video => (
                    <div key={video.id} className="video-card-home" onClick={() => loadVideo(video)}>
                      <div className="thumbnail-container" style={{ position: 'relative' }}>
                        <img src={video.thumbnail} alt={video.title} className="video-thumb-home" />
                        {video.duration && <div className="video-duration">{video.duration}</div>}
                      </div>
                      <div className="video-info-home">
                        <img
                          className="video-avatar"
                          src={getChannelAvatar(video.channelTitle, video.channelThumbnail)}
                          alt=""
                          style={{ borderRadius: '50%', objectFit: 'cover' }}
                        />
                        <div className="video-text">
                          <div className="video-title-home">{video.title}</div>
                          <div className="video-meta-home">{video.channelTitle || 'Unknown'}</div>
                          <div className="video-meta-home">{video.category} • 2M views • 👍 {video.likes ?? 0}</div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">
                    <h3>This playlist is empty</h3>
                    <p>Add some videos to get started!</p>
                  </div>
                )}
              </div>
            </>
          ) : view === 'history' ? (
            /* HISTORY VIEW */
            <div className="history-container">
              <div
                className="history-header"
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '1rem'
                }}
              >
                <div className="history-title" style={{ margin: 0 }}>
                  Watch History
                </div>
                {history.length > 0 && (
                  <button
                    onClick={clearHistory}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '20px',
                      border: '1px solid #333',
                      background: 'transparent',
                      color: '#aaa',
                      cursor: 'pointer'
                    }}
                  >
                    Clear All History
                  </button>
                )}
              </div>
              {history.length > 0 ? (
                history.map((item, index) => (
                  <div
                    key={`${item.id}-${index}`}
                    className="history-item"
                    onClick={() => loadVideo(item)}
                  >
                    <div className="history-thumb-container">
                      <img src={item.thumbnail} alt={item.title} className="history-thumb" />
                    </div>
                    <div className="history-info">
                      <div className="history-video-title">{item.title}</div>
                      <div className="history-meta">
                        {item.category} • {item.description?.substring(0, 60)}...
                      </div>
                      <div className="history-date">
                        <span>🕒 Watched on:</span>
                        {/* Format Date: "Feb 03, 2026 at 12:30 PM" */}
                        {item.watched_at ? new Date(item.watched_at).toLocaleString() : 'Just now'}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="history-empty">
                  <h3>No watch history found</h3>
                  <p>Videos you watch will appear here.</p>
                </div>
              )}
            </div>
          ) : (
            /* WATCH PAGE */
            <>
              {/* Left: Video Player */}
              <div className="video-section">
                {currentVideo ? (
                  <>
                    <div className="video-player-placeholder">
                      {currentVideo.videoUrl ? (
                        <iframe
                          className="video-player"
                          width="100%"
                          height="100%"
                          src={`${currentVideo.videoUrl}?autoplay=1&modestbranding=1&rel=0&origin=http://localhost:5173`}
                          title="YouTube video player"
                          frameBorder="0"
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                          sandbox="allow-scripts allow-same-origin allow-presentation"
                          allowFullScreen
                        ></iframe>
                      ) : (
                        <div className="error-placeholder">Video Not Available</div>
                      )}
                    </div>

                    {/* Professional Video Info Section */}
                    <div className="video-details-container">
                      <h1 className="video-main-title">{currentVideo.title}</h1>

                      <div className="video-meta-row">
                        <div className="channel-info">
                          <img
                            className="channel-avatar-lg"
                            src={getChannelAvatar(
                              currentVideo.channelTitle,
                              currentVideo.channelThumbnail
                            )}
                            alt=""
                            style={{ borderRadius: '50%', objectFit: 'cover' }}
                          />
                          <div className="channel-text">
                            <div className="channel-name">
                              {currentVideo.channelTitle || 'Content Creator'}
                            </div>
                            <div className="sub-count">
                              {subCount > 0
                                ? `${subCount} subscriber${subCount > 1 ? 's' : ''}`
                                : '0 subscribers'}
                            </div>
                          </div>
                          <button
                            className={`subscribe-btn ${isSubscribed ? 'subscribed' : ''}`}
                            onClick={handleSubscribe}
                            style={isSubscribed ? { background: '#333', color: '#fff' } : {}}
                          >
                            {isSubscribed ? 'Subscribed ✓' : 'Subscribe'}
                          </button>
                        </div>

                        <div className="video-actions">
                          <div className="action-pill">
                            <span
                              className={`like-btn ${userLikeAction === 'like' ? 'active' : ''
                                }`}
                              onClick={() => handleLike(true)}
                              style={
                                userLikeAction === 'like'
                                  ? { background: '#065fd4', color: '#fff' }
                                  : {}
                              }
                            >
                              👍 {likes > 0 ? likes : ''}
                            </span>
                            <div className="vert-divider"></div>
                            <span
                              className={`dislike-btn ${userLikeAction === 'dislike' ? 'active' : ''
                                }`}
                              onClick={() => handleLike(false)}
                              style={
                                userLikeAction === 'dislike'
                                  ? { background: '#333', color: '#fff' }
                                  : {}
                              }
                            >
                              👎 {dislikes > 0 ? dislikes : ''}
                            </span>
                          </div>
                          <button className="action-btn" onClick={() => setShowShareModal(true)}>↗ Share</button>
                          <button
                            className="action-btn"
                            onClick={() => { setVideoToSave(currentVideo); setShowPlaylistModal(true); }}
                          >
                            💾 Save
                          </button>
                          <button className="action-circle">···</button>
                        </div>
                      </div>

                      <div className="video-description-box">
                        <div className="desc-stats">
                          <span>1,240,302 views</span> • <span>{currentVideo.category}</span> •{' '}
                          <span>Jun 15, 2024</span>
                        </div>
                        <div className="tag-list">
                          {currentVideo.tags &&
                            currentVideo.tags
                              .split(',')
                              .slice(0, 5)
                              .map((tag, i) => (
                                <span key={i} className="tag">
                                  #{tag.trim()}
                                </span>
                              ))}
                        </div>
                        <p className="desc-text">
                          This is an AI-generated description for the video. In a real app, this
                          would come from the database. The Recommendation Engine uses these tags to
                          find similar content for you!
                        </p>
                      </div>

                      {/* Comments Section */}
                      <div className="comments-section">
                        <h3>
                          {comments.length} Comment
                          {comments.length !== 1 ? 's' : ''}
                        </h3>
                        <div className="add-comment">
                          <div className="user-avatar-sm"></div>
                          <input
                            type="text"
                            placeholder="Add a comment..."
                            value={commentText}
                            onChange={e => setCommentText(e.target.value)}
                            onKeyPress={e => e.key === 'Enter' && handleAddComment()}
                          />
                          {commentText.trim() && (
                            <button
                              onClick={handleAddComment}
                              style={{
                                background: '#065fd4',
                                color: '#fff',
                                border: 'none',
                                padding: '8px 16px',
                                borderRadius: '18px',
                                cursor: 'pointer',
                                marginLeft: '10px'
                              }}
                            >
                              Comment
                            </button>
                          )}
                        </div>

                        {/* Comments List */}
                        {comments.map((comment, index) => (
                          <div key={index} className="comment-item">
                            <div
                              className="user-avatar-sm"
                              style={{
                                background: `hsl(${(comment.user_id?.charCodeAt(0) || 0) * 10
                                  }, 60%, 40%)`
                              }}
                            ></div>
                            <div className="comment-text">
                              <div className="comment-header">
                                {comment.user_id}
                                <span>
                                  {' '}
                                  • {new Date(comment.timestamp).toLocaleDateString()}
                                </span>
                              </div>
                              <div className="comment-body">{comment.text}</div>
                            </div>
                          </div>
                        ))}

                        {comments.length === 0 && (
                          <div
                            style={{ textAlign: 'center', color: '#666', padding: '20px' }}
                          >
                            Be the first to comment! 💬
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <div>No video selected</div>
                )}
              </div>

              {/* Right: Recommendations */}
              <div className="recommendations">
                <div className="rec-title">Next Up</div>
                <div className="rec-list">
                  {console.log('Rendering Recs:', recommendations)}
                  {recommendations && recommendations.length > 0 ? (
                    <>
                      {recommendations.map(video => (
                        <div
                          key={video.id}
                          className="rec-card"
                          onClick={() => loadVideo(video)}
                        >
                          <div className="rec-thumb-container">
                            <img
                              src={video.thumbnail}
                              alt={video.title}
                              className="rec-thumb"
                            />
                          </div>
                          <div className="rec-info">
                            <div className="rec-video-title">{video.title}</div>
                            <div className="rec-category">{video.category}</div>
                            <div className="rec-category">👍 {video.likes ?? 0}</div>
                          </div>
                        </div>
                      ))}
                      <button
                        className="rec-more-btn"
                        onClick={() => setView('home')}
                        style={{
                          margin: '16px auto',
                          padding: '8px 24px',
                          borderRadius: '20px',
                          border: '1px solid #333',
                          background: '#1a1a1a',
                          color: '#fff',
                          cursor: 'pointer',
                          display: 'block',
                          fontSize: '0.9rem',
                          fontWeight: '500'
                        }}
                      >
                        More Videos
                      </button>
                    </>
                  ) : (
                    <div style={{ padding: 40, textAlign: 'center', color: '#888' }}>
                      <h3 style={{ marginBottom: '10px' }}>🔍 Go and Search</h3>
                      <p style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>Find more content by searching above!</p>
                      <button
                        onClick={() => document.querySelector('.search-input')?.focus()}
                        style={{
                          padding: '8px 20px',
                          borderRadius: '18px',
                          border: '1px solid #444',
                          background: 'transparent',
                          color: '#eee',
                          cursor: 'pointer'
                        }}
                      >
                        Search
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </main>
      </div>
      {/* Playlist Modal */}
      {showPlaylistModal && (
        <div className="modal-overlay" onClick={() => setShowPlaylistModal(false)}>
          <div className="playlist-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Save to...</h3>
              <button className="close-btn" onClick={() => setShowPlaylistModal(false)}>×</button>
            </div>

            <div className="playlist-list">
              <div
                className="playlist-option"
                onClick={() => handleAddToPlaylist("Watch Later", videoToSave?.id || currentVideo?.id)}
              >
                <span>🕒 Watch Later</span>
              </div>
              {userPlaylists.filter(p => p.name !== "Watch Later").map(pl => (
                <div
                  key={pl.name}
                  className="playlist-option"
                  onClick={() => handleAddToPlaylist(pl.name, videoToSave?.id || currentVideo?.id)}
                >
                  <span>📑 {pl.name}</span>
                </div>
              ))}
            </div>

            <div className="modal-footer">
              <input
                type="text"
                placeholder="Enter playlist name..."
                value={newPlaylistName}
                onChange={e => setNewPlaylistName(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && newPlaylistName && handleAddToPlaylist(newPlaylistName, videoToSave?.id || currentVideo?.id)}
              />
              <button
                className="create-btn"
                disabled={!newPlaylistName}
                onClick={() => {
                  handleAddToPlaylist(newPlaylistName, videoToSave?.id || currentVideo?.id);
                  setNewPlaylistName("");
                }}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Share Modal */}
      {showShareModal && currentVideo && (
        <div className="modal-overlay" onClick={() => setShowShareModal(false)}>
          <div className="playlist-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
            <div className="modal-header">
              <h3>Share Video</h3>
              <button className="close-btn" onClick={() => setShowShareModal(false)}>×</button>
            </div>
            
            <div className="modal-footer" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '15px', padding: '15px' }}>
              <p style={{ margin: 0, fontSize: '0.9rem', color: '#aaa' }}>Copy the link below to share.</p>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  readOnly
                  value={currentVideo.videoUrl || `https://www.youtube.com/watch?v=${currentVideo.id}`}
                  style={{ flex: 1, padding: '10px', borderRadius: '4px', border: '1px solid #444', backgroundColor: '#222', color: '#fff', fontSize: '0.9rem' }}
                />
                <button
                  className="create-btn"
                  onClick={() => {
                    const link = currentVideo.videoUrl || `https://www.youtube.com/watch?v=${currentVideo.id}`;
                    navigator.clipboard.writeText(link)
                      .then(() => {
                        alert("Link copied to clipboard!");
                        setShowShareModal(false);
                      })
                      .catch(() => alert("Failed to copy."));
                  }}
                  style={{ padding: '0 20px', whiteSpace: 'nowrap' }}
                >
                  Copy
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
