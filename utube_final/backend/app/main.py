from dotenv import load_dotenv
import os
import warnings
import sys
import json

# Load environment variables
load_dotenv(override=True)

# Disable TensorFlow logging and oneDNN info (before imports)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.database.db import (
    init_db, get_all_videos, get_video_by_id, sync_youtube_to_db, 
    _likes, _subscriptions, _comments, _saved_videos, _last_search_terms,
    record_search_term
)
from app.database.users import init_user_db, create_user, authenticate_user
from app.models.tfidf_model import Recommender
from app.services.ranking import SmartRankingEngine
from pydantic import BaseModel
from typing import Optional
import json

# Google Auth Libraries
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    print("⚠️ google-auth library not found. Using mock verification for demo.")

GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID" # Replace with actual Client ID

# Deep Learning Recommender (TensorFlow-based)
try:
    from app.models.deep_recommender import get_deep_recommender, DeepRecommender
    DEEP_LEARNING_ENABLED = True
except ImportError as e:
    print(f"[!] Deep Learning module not available: {e}")
    DEEP_LEARNING_ENABLED = False

app = FastAPI(
    title="YouTube Recommendation Engine API",
    description="Real-time video recommendations powered by Deep Learning",
    version="2.0.0"
)

# Initialize DB and start background sync
@app.on_event("startup")
async def startup_event():
    # Automatically sync some videos on startup so the home page isn't empty
    print("[ready] Server starting up. Triggering initial sync...")
    try:
        init_user_db()
        sync_youtube_to_db()
    except Exception as e:
        print(f"[!] Startup sync failed: {e}")
    print("[ready] Startup complete. Ready for requests.")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "https://youtube-eosin-tau.vercel.app",
        "https://realtime-ntube.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB and ML Models
init_db()
recommender = Recommender()  # Fallback TF-IDF recommender

# Initialize Deep Learning Recommender
deep_recommender = None
if DEEP_LEARNING_ENABLED:
    try:
        deep_recommender = get_deep_recommender()
        print(f"Model initialization: {'Successfully loaded' if deep_recommender.is_initialized else 'Fallback mode'}")
    except Exception as e:
        print(f"[!] Could not initialize Deep Recommender: {e}")

print(f"Server initialized. Model trained on {len(recommender.df)} videos.")

@app.get("/")
def read_root():
    return {"message": "YouTube Recommender API is running"}

# ============ RANKING ENGINE ============
# Ranking logic is now handled by SmartRankingEngine in smart_ranking.py

def _get_like_dislike_counts(video_id: str):
    """Return counts of likes and dislikes for a given video."""
    video_likes = _likes.get(video_id, {})
    like_count = sum(1 for v in video_likes.values() if v is True)
    dislike_count = sum(1 for v in video_likes.values() if v is False)
    return like_count, dislike_count


def _enrich_videos_with_like_counts(videos):
    """Mutate a list of video dicts to include like/dislike counts."""
    for video in videos:
        if not video or not isinstance(video, dict):
            continue
        vid_id = video.get('id')
        if not vid_id:
            continue
        likes, dislikes = _get_like_dislike_counts(vid_id)
        video['likes'] = likes
        video['dislikes'] = dislikes
    return videos


@app.get("/videos")
def get_videos(q: str = None, category: str = None, user_id: str = "demo_user_123", t: str = None):
    """
    Standard YouTube Video Endpoint.
    Now utilizes the Advanced Ranking System for high-relevance results.
    """
    from app.database.db import search_videos, get_user_history, get_all_videos, get_video_by_id
    
    # 1. Personalization Context
    history = get_user_history(user_id)
    from app.database.db import get_user_interest_queries
    
    user_id_str = str(user_id)
    user_profile = {
        "id": user_id_str,
        "subscribed_channels": [cid for cid, uids in _subscriptions.items() if user_id_str in uids],
        "watch_history": [h['video_id'] for h in history],
        "liked_categories": [],
        "interest_topics": get_user_interest_queries(user_id_str, max_queries=5)
    }
    
    # Identify liked categories from likes state
    for vid_id, user_actions in _likes.items():
        if user_actions.get(user_id_str) is True:
            v = get_video_by_id(vid_id)
            if v: user_profile["liked_categories"].append(v.get('category'))

    # Initialize Advanced Ranking Engine
    engine = SmartRankingEngine(user_profile, global_stats={"likes": _likes, "comments": _comments})

    # 2. Search Logic (with Ranking)
    if q:
        # Record search term for personalization
        record_search_term(user_id_str, q)
        
        # Fetch a larger pool of candidates (50) to allow ranking to pick the best 25
        candidates = search_videos(q, max_results=50)
        # Return smart-ranked results
        return _enrich_videos_with_like_counts(engine.rank(candidates, user_query=q, top_n=25))
    
    # 3. Category Logic
    if category and category.lower() != "all":
        from app.database.db import ensure_category_content
        candidates = ensure_category_content(category)
        return _enrich_videos_with_like_counts(engine.rank(candidates, user_query=category, top_n=30))
    
    # 4. Default Home Feed (Personalized & Fresh)
    searches = _last_search_terms.get(user_id_str, [])
    has_likes = any(user_actions.get(user_id_str) is True for user_actions in _likes.values())

    if not history and not searches and not has_likes:
        # NEW REQUIREMENT: If No Signals (New/Reset ID), display nothing.
        # User must search or interact first.
        return []
        
    # User has signals: Get all videos and rank them
    all_videos = get_all_videos()
    return _enrich_videos_with_like_counts(engine.rank(all_videos, user_query="recommended", top_n=60))

@app.get("/videos/{video_id}")
def get_video(video_id: str):
    """Return a specific video by ID."""
    video = get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Include current like/dislike counts in the response
    likes, dislikes = _get_like_dislike_counts(video_id)
    video_copy = dict(video)
    video_copy['likes'] = likes
    video_copy['dislikes'] = dislikes
    return video_copy

from pydantic import BaseModel

class InteractionRequest(BaseModel):
    user_id: str
    video_id: str
    action: str = "click"


@app.post("/interaction")
def track_interaction(request: InteractionRequest):
    """Log user interaction for personalization."""
    from app.database.db import log_interaction
    log_interaction(request.user_id, request.video_id, request.action)
    return {"status": "success"}

@app.get("/recommend/{video_id}")
def recommend(video_id: str, user_id: str = "guest_user", use_deep_learning: bool = True):
    """
    Return recommended videos using Deep Learning + Hybrid logic.
    Now strictly filtered by history interests.
    """
    from app.database.db import get_user_history, fetch_related_videos, get_user_interest_queries
    
    video = get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # 1. Proactively fetch related videos
    try:
        fetch_related_videos(video_id, max_results=25)
    except Exception as e:
        print(f"[!] Could not fetch related from YT: {e}")

    # 2. Get Context
    all_videos = get_all_videos()
    user_history = get_user_history(user_id)
    
    # Initialize Engine for strict history filtering
    history_ids = [h['video_id'] for h in user_history]
    liked_cats = []
    for vid_id, user_actions in _likes.items():
        if user_actions.get(user_id) is True:
            v = get_video_by_id(vid_id)
            if v: liked_cats.append(v.get('category'))

    interest_topics = get_user_interest_queries(user_id, max_queries=5)

    if not history_ids and not liked_cats and not interest_topics:
        # NO SIGNALS: Return empty list as per strict personalization requirement
        return []

    user_profile = {
        "id": user_id,
        "watch_history": history_ids,
        "liked_categories": liked_cats,
        "interest_topics": interest_topics,
        "subscribed_channels": [cid for cid, uids in _subscriptions.items() if user_id in uids],
    }
    engine = SmartRankingEngine(user_profile, global_stats={"likes": _likes, "comments": _comments})

    # 3. STRICT FILTERING: Only recommend videos EXACTLY inside history, likes, or playlists
    from app.database.db import get_strict_user_videos
    candidate_videos = get_strict_user_videos(user_id)
    
    # If the candidate list is empty, there's nothing to recommend strictly
    if not candidate_videos:
        # Optionally fallback to all_videos if they wanted something, but the requirement is "only recommend".
        return []
        
    # Still rank the strictly fetched videos so the best match comes first
    return _enrich_videos_with_like_counts(engine.rank(candidate_videos, user_query="recommended", top_n=40))

@app.get("/history/{user_id}")
def get_history(user_id: str):
    """Return watched video history for a user."""
    from app.database.db import get_enriched_history
    return get_enriched_history(user_id)

@app.delete("/history/{user_id}")
def delete_history(user_id: str):
    """Clear all personal data for a user (History, Playlists, etc)."""
    from app.database.db import clear_all_user_data
    clear_all_user_data(user_id)
    return {"status": "success", "message": "All user data cleared"}

@app.get("/sync")
def sync_data():
    """Force sync with YouTube API."""
    from app.database.db import sync_youtube_to_db
    from app.models.tfidf_model import Recommender
    sync_youtube_to_db()
    # Re-initialize recommender to pick up new data
    global recommender, deep_recommender
    recommender = Recommender()
    
    # Refresh deep recommender's video index
    if deep_recommender and deep_recommender.is_initialized:
        deep_recommender.build_video_index(get_all_videos())
    
    return {"status": "Database updated with real-time YouTube data"}

@app.get("/suggestions")
def get_suggestions(q: str = ""):
    """Rapid suggestion endpoint for search bar."""
    if not q or len(q) < 2:
        return []
    
    from app.database.db import _youtube_videos
    from app.database.data import VIDEO_DATA
    
    q_lower = q.lower()
    matches = []
    seen_ids = set()
    
    # 1. Search in synced videos
    for v in _youtube_videos:
        if q_lower in v["title"].lower():
            matches.append({"id": v["id"], "title": v["title"]})
            seen_ids.add(v["id"])
            if len(matches) >= 10: break
            
    # 2. Search in mock data if we need more
    if len(matches) < 10:
        for v in VIDEO_DATA:
            if v["id"] not in seen_ids and q_lower in v["title"].lower():
                matches.append({"id": v["id"], "title": v["title"]})
                seen_ids.add(v["id"])
                if len(matches) >= 10: break
                
    return matches[:8]

@app.get("/status")
def get_status():
    """
    Get the status of the recommendation engine.
    Useful for debugging and monitoring.
    """
    return {
        "api_version": "2.0.0",
        "deep_learning_available": DEEP_LEARNING_ENABLED,
        "deep_learning_model_loaded": deep_recommender.is_initialized if deep_recommender else False,
        "total_videos": len(recommender.df) if hasattr(recommender, 'df') else 0,
        "recommendation_mode": "deep_learning" if (deep_recommender and deep_recommender.is_initialized) else "tfidf_hybrid"
    }

@app.get("/clear")
def clear_youtube_data():
    """Clear synced YouTube videos and use mock data instead."""
    from app.database.db import clear_synced_videos
    from app.models.tfidf_model import Recommender
    
    clear_synced_videos()
    
    # Re-initialize recommender with mock data
    global recommender
    recommender = Recommender()
    
# ============ AUTHENTICATION ============
class GoogleAuthRequest(BaseModel):
    credential: str

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

@app.post("/signup")
def signup(request: SignupRequest):
    """Create a new user account."""
    try:
        user = create_user(request.name, request.email, request.password)
        if not user:
            raise HTTPException(status_code=400, detail="Email already registered")
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
def login_email(request: LoginRequest):
    """Authenticated login with SQLite."""
    user = authenticate_user(request.email, request.password)
    if user:
        user["status"] = "success"
        return user
    else:
        raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/auth/google")
def authenticate_google(request: GoogleAuthRequest):
    """Verify Google ID Token and return user info."""
    if GOOGLE_AUTH_AVAILABLE:
        try:
            # Re-verify the token server-side
            idinfo = id_token.verify_oauth2_token(
                request.credential, 
                google_requests.Request(), 
                GOOGLE_CLIENT_ID
            )
            
            # ID token is valid. Get the user's Google ID from the decoded token.
            return {
                "id": idinfo['sub'],
                "email": idinfo['email'],
                "name": idinfo.get('name', 'Google User'),
                "picture": idinfo.get('picture'),
                "status": "success"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Google Token: {str(e)}")
    else:
        # Fallback for demo if library not installed
        import base64
        try:
            # Simulate decoding a JWT for demo purposes
            # (In a real app, ALWAYS use the official library)
            return {
                "id": "google_demo_12345",
                "email": "user@gmail.com",
                "name": "Demo User",
                "picture": "https://lh3.googleusercontent.com/a/default-user",
                "status": "demo_success"
            }
        except:
             raise HTTPException(status_code=400, detail="Auth verification failed")

@app.get("/admin/users")
def get_admin_users():
    """Admin endpoint to see all registered users."""
    from app.database.users import get_db
    try:
        db = get_db()
        if db is None:
            return {"status": "error", "detail": "Database connection failed"}
            
        users_collection = db.users
        users = []
        for user in users_collection.find({}, {"password": 0}): # Exclude parsing hashed passwords
            users.append({
                "id": str(user["_id"]),
                "name": str(user.get("name", "")),
                "email": str(user.get("email", "")),
                "avatar": str(user.get("avatar", ""))
            })
            
        return {"total_users": len(users), "users": users}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ============ SOCIAL FEATURES ============
# Storage moved to db.py for consistency and persistence support

# ============ RANKING ENGINE ============
# Ranking logic is now handled by SmartRankingEngine in smart_ranking.py

class LikeRequest(BaseModel):
    user_id: str
    video_id: str
    is_like: bool  # True = like, False = dislike

class CommentRequest(BaseModel):
    user_id: str
    video_id: str
    text: str

class SubscribeRequest(BaseModel):
    user_id: str
    channel_id: str

@app.post("/like")
def like_video(request: LikeRequest):
    """Like or dislike a video."""
    if request.video_id not in _likes:
        _likes[request.video_id] = {}
    
    _likes[request.video_id][request.user_id] = request.is_like
    
    # Count likes and dislikes
    video_likes = _likes.get(request.video_id, {})
    like_count = sum(1 for v in video_likes.values() if v == True)
    dislike_count = sum(1 for v in video_likes.values() if v == False)
    
    return {
        "status": "success",
        "likes": like_count,
        "dislikes": dislike_count,
        "user_action": "like" if request.is_like else "dislike"
    }

@app.get("/likes/{video_id}")
def get_likes(video_id: str, user_id: str = "guest"):
    """Get like/dislike counts and user's current action."""
    video_likes = _likes.get(video_id, {})
    like_count = sum(1 for v in video_likes.values() if v == True)
    dislike_count = sum(1 for v in video_likes.values() if v == False)
    user_action = None
    if user_id in video_likes:
        user_action = "like" if video_likes[user_id] else "dislike"
    
    return {
        "likes": like_count,
        "dislikes": dislike_count,
        "user_action": user_action
    }

@app.post("/subscribe")
def subscribe_channel(request: SubscribeRequest):
    """Subscribe or unsubscribe from a channel."""
    if request.channel_id not in _subscriptions:
        _subscriptions[request.channel_id] = set()
    
    if request.user_id in _subscriptions[request.channel_id]:
        _subscriptions[request.channel_id].remove(request.user_id)
        action = "unsubscribed"
    else:
        _subscriptions[request.channel_id].add(request.user_id)
        action = "subscribed"
        
        # TRIGGER: Fetch more videos from this channel to populate feed
        # User just showed strong interest
        try:
             from app.database.db import fetch_channel_videos
             # Run in background ideally, but here synchronous for demo speed
             fetch_channel_videos(request.channel_id, channel_title="Subscribed Channel")
        except Exception as e:
            print(f"[!] Failed to sync subscribed channel content: {e}")
    
    return {
        "status": "success",
        "action": action,
        "subscriber_count": len(_subscriptions[request.channel_id])
    }

@app.get("/subscribed/{channel_id}")
def check_subscription(channel_id: str, user_id: str = "guest"):
    """Check if user is subscribed to a channel."""
    subs = _subscriptions.get(channel_id, set())
    return {
        "is_subscribed": user_id in subs,
        "subscriber_count": len(subs)
    }

@app.post("/comment")
def add_comment(request: CommentRequest):
    """Add a comment to a video."""
    from datetime import datetime
    
    if request.video_id not in _comments:
        _comments[request.video_id] = []
    
    comment = {
        "user_id": request.user_id,
        "text": request.text,
        "timestamp": datetime.now().isoformat(),
        "likes": 0
    }
    _comments[request.video_id].insert(0, comment)  # Newest first
    
    return {
        "status": "success",
        "comment": comment,
        "total_comments": len(_comments[request.video_id])
    }

@app.get("/comments/{video_id}")
def get_comments(video_id: str):
    """Get all comments for a video."""
    comments = _comments.get(video_id, [])
    return {
        "comments": comments,
        "total": len(comments)
    }

class SaveRequest(BaseModel):
    user_id: str
    video_id: str

class PlaylistRequest(BaseModel):
    user_id: str
    playlist_name: str
    video_id: str

@app.post("/save")
def save_video(request: SaveRequest):
    """Save a video to user's list."""
    if request.user_id not in _saved_videos:
        _saved_videos[request.user_id] = []
    
    if request.video_id not in _saved_videos[request.user_id]:
        _saved_videos[request.user_id].insert(0, request.video_id) # Newest first
        action = "saved"
    else:
        # Toggle: if already saved, remove it? 
        # Usually Save button is a toggle. Let's make it add only here, 
        # and support remove via delete or toggle logic. 
        # Let's assume this endpoint is for ADD/TOGGLE.
        _saved_videos[request.user_id].remove(request.video_id)
        action = "removed"
        
    return {
        "status": "success",
        "action": action,
        "saved_count": len(_saved_videos[request.user_id])
    }

@app.get("/saved/{user_id}")
def get_saved_videos(user_id: str):
    """Get all saved videos for a user."""
    video_ids = _saved_videos.get(user_id, [])
    
    # Enrich with video details
    saved_list = []
    for vid_id in video_ids:
        video = get_video_by_id(vid_id)
        if video:
            saved_list.append(video)
            
    return saved_list

@app.get("/is_saved/{video_id}")
def check_is_saved(video_id: str, user_id: str):
    """Check if a video is saved by user."""
    user_list = _saved_videos.get(user_id, [])
    return {"is_saved": video_id in user_list}

# ============ PLAYLIST ENDPOINTS ============
@app.post("/playlists/add")
def add_video_to_playlist(request: PlaylistRequest):
    """Add a video to a specific playlist."""
    from app.database.db import add_to_playlist
    success = add_to_playlist(request.user_id, request.playlist_name, request.video_id)
    return {"status": "success" if success else "already_exists"}

@app.post("/playlists/remove")
def remove_video_from_playlist(request: PlaylistRequest):
    """Remove a video from a specific playlist."""
    from app.database.db import remove_from_playlist
    success = remove_from_playlist(request.user_id, request.playlist_name, request.video_id)
    return {"status": "success" if success else "failed"}

@app.get("/playlists/{user_id}")
def get_user_playlists(user_id: str):
    """Get all playlists for a user."""
    from app.database.db import get_user_playlists
    playlists = get_user_playlists(user_id)
    # Convert to a format easy for frontend
    return [{"name": name, "count": len(vids)} for name, vids in playlists.items()]

@app.get("/playlists/{user_id}/{playlist_name}")
def get_playlist_content(user_id: str, playlist_name: str):
    """Get videos within a specific playlist."""
    from app.database.db import get_playlist_videos
    return get_playlist_videos(user_id, playlist_name)

@app.get("/liked/{user_id}")
def get_user_liked_videos(user_id: str):
    """Get all videos liked by a user."""
    from app.database.db import get_liked_videos
    return get_liked_videos(user_id)

@app.delete("/liked/{user_id}")
def delete_user_liked_videos(user_id: str):
    """Clear all liked videos for a user."""
    from app.database.db import clear_liked_videos
    clear_liked_videos(user_id)
    return {"status": "success", "message": "Liked videos cleared"}

@app.get("/disliked/{user_id}")
def get_user_disliked_videos(user_id: str):
    """Get all videos disliked by a user."""
    from app.database.db import get_disliked_videos
    return get_disliked_videos(user_id)

@app.delete("/disliked/{user_id}")
def delete_user_disliked_videos(user_id: str):
    """Clear all disliked videos for a user."""
    from app.database.db import clear_disliked_videos
    clear_disliked_videos(user_id)
    return {"status": "success", "message": "Disliked videos cleared"}

