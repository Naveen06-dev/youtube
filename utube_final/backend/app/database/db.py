import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build

# Load environment variables from .env file
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

if not YOUTUBE_API_KEY:
    print("❌ ERROR: YOUTUBE_API_KEY not found in .env file!")
    print("Please add 'YOUTUBE_API_KEY=your_key_here' to the .env file in the backend directory.")


_youtube_videos = []  
_search_cache = {}    # Stores search results temporarily (Dict[VideoID, VideoData])
_user_interactions = []  # Stores user watch history
_likes = {}           # Stores video likes/dislikes
_subscriptions = {}    # Stores channel subscriptions
_comments = {}        # Stores video comments
_saved_videos = {}    # Stores saved videos per user
_last_search_terms = {} # Stores last search terms per user
_playlists = {}       # Stores playlists per user: {user_id: {name: [video_ids]}}
_query_results_cache = {} # {query: (timestamp, [videos])}

_youtube_client = None

def get_youtube_client():
    """Initialize and return a cached YouTube API client."""
    global _youtube_client
    if _youtube_client:
        return _youtube_client
        
    try:
        _youtube_client = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY, static_discovery=False)
        return _youtube_client
    except Exception as e:
        print(f"[ERROR] Failed to initialize YouTube client: {e}")
        return None

# ============ INITIALIZATION ============
def init_db():
    """Initialize the database (in-memory mode)."""
    print("[INFO] Running in IN-MEMORY mode (no external database required)")
    print("[INFO] YouTube API is available for fetching real videos")
    return True

def clear_synced_videos():
    """Clear all YouTube synced videos and use mock data instead."""
    global _youtube_videos
    _youtube_videos = []
    print("[INFO] Cleared synced videos - now using mock data")
    return True

# ============ HELPERS ============
import re

def parse_duration(pt_duration):
    """Parse ISO 8601 duration (PT#H#M#S) to seconds."""
    hours = 0
    minutes = 0
    seconds = 0
    
    # Check for Hours
    h_match = re.search(r'(\d+)H', pt_duration)
    if h_match:
        hours = int(h_match.group(1))
    
    # Check for Minutes
    m_match = re.search(r'(\d+)M', pt_duration)
    if m_match:
        minutes = int(m_match.group(1))
    
    # Check for Seconds
    s_match = re.search(r'(\d+)S', pt_duration)
    if s_match:
        seconds = int(s_match.group(1))
    
    return hours * 3600 + minutes * 60 + seconds

def format_duration(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

# ============ YOUTUBE API FUNCTIONS ============
def fetch_youtube_videos(query="trending", max_results=10, category_name="YouTube", fetch_logos=True):
    # ... (Implementation checks client) ...
    client = get_youtube_client()
    if not client:
        print("[!] YouTube client not available")
        return []

    try:
        print(f"[search] Fetching '{query}' from YouTube...")
        request = client.search().list(
            part="snippet",
            maxResults=min(max_results, 50),
            q=query,
            type="video",
            videoEmbeddable="true",
            safeSearch="moderate"
        )
        response = request.execute()
        
        videos = []
        video_ids = []
        
        # 1. Collect Video IDs from Search
        for item in response.get("items", []):
            id_data = item.get("id", {})
            video_id = id_data.get("videoId")
            if video_id:
                video_ids.append(video_id)
        
        if not video_ids:
            return []

        # 2. Batch Fetch Video Details (ContentDetails for Duration, Snippet for correct info)
        try:
            vid_req = client.videos().list(
                part="snippet,contentDetails",
                id=",".join(video_ids[:50])
            )
            vid_res = vid_req.execute()
            
            channel_ids = set()
            


            for item in vid_res.get("items", []):
                snippet = item["snippet"]
                content_details = item["contentDetails"]
                duration_iso = content_details.get("duration", "PT0S")
                
                # Filter Shorts: Increase threshold to 90s to catch "1 minute" videos
                # parse_duration is now global
                duration_seconds = parse_duration(duration_iso)
                
                if duration_seconds <= 90:
                    continue

                video_id = item["id"]
                channel_id = snippet.get("channelId")
                if channel_id: channel_ids.add(channel_id)
                
                formatted_duration = format_duration(duration_seconds)

                video = {
                    "id": video_id,
                    "title": snippet["title"],
                    "thumbnail": snippet["thumbnails"].get("high", {}).get("url") or snippet["thumbnails"]["default"]["url"],
                    "category": category_name,
                    "duration": formatted_duration,
                    "tags": f"{snippet['title']}, {snippet.get('description', '')[:200]}",
                    "description": snippet.get("description", "")[:500],
                    "videoUrl": f"https://www.youtube.com/embed/{video_id}",
                    
                    "channelTitle": snippet.get("channelTitle", "Unknown"),
                    "channelId": channel_id,
                    "channelThumbnail": "",
                    "publishedAt": snippet.get("publishedAt", "")
                }
                videos.append(video)
                
        except Exception as e:
            print(f"[!] Error fetching video details: {e}")
            return []
        
        # 3. Batch Fetch Channel Logos (Optional for speed)
        channel_logos = {}
        if fetch_logos and channel_ids:
            try:
                ids_list = list(channel_ids)[:50] 
                chan_req = client.channels().list(part="snippet", id=",".join(ids_list))
                chan_res = chan_req.execute()
                for ch in chan_res.get("items", []):
                    thumbs = ch["snippet"]["thumbnails"]
                    thumb_url = thumbs.get("default", {}).get("url") or thumbs.get("medium", {}).get("url")
                    channel_logos[ch["id"]] = thumb_url
            except Exception as e:
                print(f"[!] Could not fetch channel logos: {e}")
 
        for v in videos:
            if v.get("channelId") in channel_logos:
                v["channelThumbnail"] = channel_logos[v.get("channelId")]

        print(f"   [OK] Fetched {len(videos)} videos for '{query}' (Filtered Shorts)")
        return videos
        
    except Exception as e:
        print(f"[ERROR] Error fetching from YouTube: {e}")
        return []

def fetch_related_videos(video_id, max_results=10):
    # Fetch related and store in _search_cache (ephemeral)
    # They should NOT go to _youtube_videos immediately to keep Home clean.
    client = get_youtube_client()
    if not client: return []

    video = get_video_by_id(video_id)
    if not video: return []

    try:
        search_query = video['title']
        if video.get('tags'):
            first_tag = video['tags'].split(',')[0].strip()
            if len(first_tag) > 3: search_query = first_tag

        print(f"[rec] Fetching videos related to '{search_query}'...")
        request = client.search().list(
            part="snippet",
            maxResults=max_results,
            q=search_query,
            type="video",
            videoEmbeddable="true"
        )
        response = request.execute()
        
        # 1. Get raw search results (Video IDs)
        # We need video IDs first to fetch details (duration) for filtering
        video_ids = []
        for item in response.get("items", []):
            vid_id = item["id"].get("videoId")
            if vid_id and vid_id != video_id:
                video_ids.append(vid_id)
        
        if not video_ids:
            return []

        # 2. Fetch Details (Duration check)
        vid_req = client.videos().list(
            part="snippet,contentDetails",
            id=",".join(video_ids)
        )
        vid_res = vid_req.execute()
        
        videos = []
        for item in vid_res.get("items", []):
            snippet = item["snippet"]
            content_details = item["contentDetails"]
            duration_iso = content_details.get("duration", "PT0S")
            
            # Filter Shorts (Global helper)
            duration_seconds = parse_duration(duration_iso)
            if duration_seconds <= 90:
                continue

            vid_id = item["id"]
            
            video_data = {
                "id": vid_id,
                "title": snippet["title"],
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url") or snippet["thumbnails"]["default"]["url"],
                "category": "Recommended",
                "duration": format_duration(duration_seconds),
                "tags": f"{snippet['title']}, {snippet.get('description', '')[:200]}",
                "description": snippet.get("description", "")[:500],
                "videoUrl": f"https://www.youtube.com/embed/{vid_id}",
                "channelTitle": snippet.get("channelTitle", "Unknown"),
                "channelId": snippet.get("channelId"),
                "channelThumbnail": "", # Could fetch if needed, but skipping for speed
                "publishedAt": snippet.get("publishedAt", "")
            }
            videos.append(video_data)
        
        # 3. Add to Main Pool (Home Feed) AND Cache
        # This fixes "Watch -> No Recommendations" issue.
        global _search_cache, _youtube_videos
        
        existing_ids = {v['id'] for v in _youtube_videos}
        new_videos_count = 0
        
        for v in videos:
            _search_cache[v['id']] = v
            # PROMOTION: Populate Home Feed with these recommendations
            if v['id'] not in existing_ids:
                _youtube_videos.append(v)
                existing_ids.add(v['id'])
                new_videos_count += 1
        
        print(f"   [OK] Fetched {len(videos)} related videos (Filtered Shorts)")
        print(f"   [promo] Added {new_videos_count} new videos to Home Feed")
        return videos
    except Exception as e:
        print(f"[ERROR] Error fetching related: {e}")
        return []

def search_videos(query, max_results=20):
    """
    Search for videos.
    Prioritizes FRESH results from YouTube API over local ones to ensure "new new ones".
    Uses query caching to significantly speed up repeated searches.
    """
    global _query_results_cache, _search_cache
    
    query_key = query.lower().strip()
    
    # 1. Check Query Cache (Valid for 10 minutes)
    if query_key in _query_results_cache:
        ts, cached_videos = _query_results_cache[query_key]
        if (datetime.now() - ts).total_seconds() < 600: # 10 mins
            print(f"[cache] Returning cached results for '{query}'")
            return cached_videos[:max_results]

    # 1. Always fetch from YouTube API for fresh content if not in cache
    # Set fetch_logos=False for search to speed up the result return
    new_videos = fetch_youtube_videos(query=query, max_results=max_results, category_name="Search result", fetch_logos=False)
    
    # 3. Also look in Local Home Feed for variety/offline support
    all_local = get_all_videos()
    local_results = [
        v for v in all_local 
        if query.lower() in v['title'].lower() or query.lower() in v.get('tags', '').lower()
    ]
    
    # 4. Cache fresh results in the Video Object Cache
    for v in new_videos:
        _search_cache[v['id']] = v
            
    # Combine: [Fresh API Results] + [Local Matches] (Avoiding duplicates)
    fresh_ids = {v['id'] for v in new_videos}
    combined = new_videos + [v for v in local_results if v['id'] not in fresh_ids]
    results = combined[:max_results]
    
    # 5. Update Query Cache
    if results:
        _query_results_cache[query_key] = (datetime.now(), results)
    
    return results

def record_search_term(user_id, query):
    """Record a search term for a user to use in personalization."""
    global _last_search_terms
    u_id = str(user_id)
    if not query or len(query) < 3:
        return
    
    if u_id not in _last_search_terms:
        _last_search_terms[u_id] = []
    
    # Keep last 5 unique queries
    if query not in _last_search_terms[u_id]:
        _last_search_terms[u_id].insert(0, query)
        _last_search_terms[u_id] = _last_search_terms[u_id][:5]

def sync_youtube_to_db():
    global _youtube_videos
    import random
    print("\n" + "="*50)
    print("[sync] SYNCING REAL-TIME DATA FROM YOUTUBE")
    print("="*50)
    
    # Pool of potential queries to fetch fresh content
    query_pool = [
        ("gaming highlights 2024", "Gaming", 15),
        ("latest tech reviews 2024", "Tech", 15),
        ("popular music hits 2024", "Music", 15),
        ("easy recipes for dinner", "Cooking", 15),
        ("best travel destinations 2024", "Travel", 15),
        ("stand up comedy 2024", "Comedy", 15),
        ("learn python programming", "Education", 15),
        ("football highlights 2024", "Sports", 15),
        ("global news today", "News", 15),
        ("fitness workout at home", "Health", 15),
        ("movie trailers 2024", "Entertainment", 15),
        ("funny cats and dogs", "Comedy", 15)
    ]
    
    # Pick 4 random categories, and add variety to the query itself
    # We use random.choice/sample to ensure different results on every sync click
    categories = random.sample(query_pool, min(len(query_pool), 4))
    
    all_videos = []
    for query, category, count in categories:
        videos = fetch_youtube_videos(query=query, max_results=count, category_name=category)
        all_videos.extend(videos)
    
    if all_videos:
        # Append to existing (Merge)
        existing_ids = {v['id'] for v in _youtube_videos}
        new_count = 0
        for v in all_videos:
            if v['id'] not in existing_ids:
                _youtube_videos.append(v)
                existing_ids.add(v['id'])
                new_count += 1
        
        print("\n" + "="*50)
        print(f"[OK] SYNC COMPLETE: Added {new_count} NEW videos! Total in DB: {len(_youtube_videos)}")
        print("="*50 + "\n")
        return {"status": "success", "new_videos": new_count, "total": len(_youtube_videos)}
    else:
        # It's okay to be empty initially if we rely on search
        print("ℹ️ Sync finished but no videos returned.")
        return {"status": "success", "count": 0}

# ============ VIDEO RETRIEVAL ============
def get_all_videos():
    """
    Get all available videos (HOME FEED).
    ONLY returns videos explicitly tracked in the main pool.
    Excludes ephemeral search results.
    """
    from .data import VIDEO_DATA
    # Note: _youtube_videos is global, but since we only read it, no 'global' keyword is strictly needed.
    video_map = {v['id']: v for v in _youtube_videos}
    for v in VIDEO_DATA:
        if v['id'] not in video_map:
            video_map[v['id']] = v
    
    # Safety Check: Ensure every video has an embed URL
    for vid, data in video_map.items():
        if 'videoUrl' not in data:
            data['videoUrl'] = f"https://www.youtube.com/embed/{vid}"
            
    return list(video_map.values())

def get_video_by_id(video_id):
    """
    Get a specific video by its ID.
    Checks: Main Pool -> Search Cache -> Mock Data
    """
    video = None
    
    # 1. Main Pool
    for v in _youtube_videos:
        if v['id'] == video_id:
            video = v
            break
    
    # 2. Search Cache
    if not video and video_id in _search_cache:
        video = _search_cache[video_id]

    # 3. Mock Data
    if not video:
        from .data import VIDEO_DATA
        video = next((v for v in VIDEO_DATA if v["id"] == video_id), None)
    
    if video and 'videoUrl' not in video:
        # Compatibility fix: ensure videoUrl is present
        video = video.copy() # Don't mutate if it's from VIDEO_DATA
        video['videoUrl'] = f"https://www.youtube.com/embed/{video_id}"
        
    return video

# ============ USER INTERACTIONS (IN-MEMORY) ============
def log_interaction(user_id, video_id, action_type="click"):
    """
    Log interaction. 
    CRITICAL: If a user interacts with a cached search result, PROMOTE it to the Main Pool.
    """
    global _user_interactions, _youtube_videos
    
    # 1. Log the interaction
    u_id = str(user_id)
    interaction = {
        "user_id": u_id,
        "video_id": video_id,
        "action": action_type,
        "timestamp": datetime.now().isoformat()
    }
    _user_interactions.append(interaction)
    print(f"[log] Logged: {u_id} -> {action_type} -> {video_id}")
    
    # 2. Promotion Logic (Search/Rec -> Home Feed)
    # Check if this video is in our Search Cache but NOT in Main Pool
    existing_ids = {v['id'] for v in _youtube_videos}
    
    if video_id not in existing_ids and video_id in _search_cache:
        print(f"[promo] Promoting video {video_id} from Cache to Home Feed!")
        _youtube_videos.append(_search_cache[video_id])

def get_user_history(user_id):
    """Fetch all interactions for a specific user."""
    u_id = str(user_id)
    return [i for i in _user_interactions if i["user_id"] == u_id]

def clear_user_history(user_id):
    """Clear all history for a specific user."""
    global _user_interactions
    u_id = str(user_id)
    # Keep interactions that are NOT from this user
    _user_interactions = [i for i in _user_interactions if i["user_id"] != u_id]
    print(f"[clean] Cleared history for user: {u_id}")
    return True

def clear_all_user_data(user_id):
    """Full reset: Clear history, playlists, likes, and saved videos for a user."""
    global _user_interactions, _playlists, _likes, _saved_videos, _subscriptions
    u_id = str(user_id)
    
    # 1. Clear History
    clear_user_history(u_id)
    
    # 2. Clear Playlists
    if u_id in _playlists:
        _playlists[u_id] = {"Watch Later": []}
        
    # 3. Clear Saved Videos
    if u_id in _saved_videos:
        _saved_videos[u_id] = []
        
    # 4. Clear Likes/Dislikes
    for vid_id in _likes:
        if u_id in _likes[vid_id]:
            _likes[vid_id].pop(u_id, None)
            
    # 5. Clear Subscriptions
    for chan_id in _subscriptions:
        if u_id in _subscriptions[chan_id]:
            _subscriptions[chan_id].discard(u_id)

    # 6. Clear Search Terms
    if u_id in _last_search_terms:
        _last_search_terms[u_id] = []

    # 7. Clear User Comments (Remove identifying comments from the video maps)
    for vid_id in _comments:
        _comments[vid_id] = [c for c in _comments[vid_id] if str(c.get('user_id')) != u_id]
            
    print(f"[clean] Full data reset complete for user: {u_id}")
    return True

def get_enriched_history(user_id):
    """Fetch history with full video details and timestamps."""
    history = get_user_history(user_id)
    
    # Sort by timestamp (newest first)
    history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    enriched = []
    seen_ids = set()
    
    for item in history:
        vid_id = item.get('video_id')
        if not vid_id or vid_id in seen_ids:
            continue
        
        seen_ids.add(vid_id)
        video_data = get_video_by_id(vid_id)
        
        if video_data:
            video_copy = video_data.copy()
            video_copy['watched_at'] = item.get('timestamp')
            enriched.append(video_copy)
    
    return enriched

def get_user_interest_queries(user_id, max_queries=5):
    """Extract potential search queries based on user's watch history."""
    history = get_enriched_history(user_id)
    # Use most recent video titles/categories
    queries = []

    # 0. Recently searched terms (High priority)
    searches = _last_search_terms.get(user_id, [])
    queries.extend(searches)
    
    # 1. Recently liked categories
    liked_cats = []
    for vid_id, actions in _likes.items():
        if actions.get(user_id) is True:
            v = get_video_by_id(vid_id)
            if v: liked_cats.append(v.get('category'))
    
    if liked_cats:
        # Add all unique liked categories
        queries.extend(list(set(liked_cats)))
        
    # 2. Keywords from recent titles
    # Extract significant phrases from the last 10 videos
    recent_titles = [v['title'] for v in history[:10]]
    for title in recent_titles:
        # Avoid single-word generic terms. Look for capitalization or longer phrases.
        # Simple heuristic: ignore very common broad words
        blacklisted = {"fear", "throttle", "products", "stuff", "latest", "update", "today", "video"}
        words = [w.strip("(),.-").lower() for w in title.split() if len(w) > 3]
        
        # Filter out blacklisted words and very common ones
        meaningful_words = [w for w in words if w not in blacklisted]
        
        if len(meaningful_words) >= 2:
            # Add a 2-word phrase which is much more specific than a single word
            queries.append(" ".join(meaningful_words[:2]))
        elif meaningful_words:
            # Only add single words if they are quite long (likely specific)
            if len(meaningful_words[0]) > 6:
                queries.append(meaningful_words[0])
            
    # Remove duplicates and limit
    unique_queries = []
    for q in queries:
        if q and q not in unique_queries:
            unique_queries.append(q)
            
    return unique_queries[:max_queries]

# ============ MANUAL SYNC (for testing) ============

# ============ CATEGORY AUTO-FETCH ============
def ensure_category_content(category):
    """If a category has few videos, fetch fresh ones from YouTube."""
    global _youtube_videos
    
    # 1. Check existing count
    existing = [v for v in _youtube_videos if v.get('category', '').lower() == category.lower()]
    if len(existing) >= 8: # If we have at least 8, that's enough to start
         return existing

    # 2. Define Query Map
    query_map = {
        "gaming": "gaming highlights 2024",
        "tech": "latest tech gadgets review 2024",
        "music": "top music hits 2024",
        "cooking": "delicious easy recipes",
        "travel": "best travel destinations vlog",
        "comedy": "funny comedy skits 2024",
        "education": "python programming tutorial for beginners", # Keep coding flavor
        "sports": "sports highlights 2024",
        "news": "world news today",
    }
    
    search_query = query_map.get(category.lower(), f"{category} trending videos")
    print(f"[cat] Auto-fetching category '{category}' with query '{search_query}'")
    
    # Fetch 20 videos to populate the category well
    new_videos = fetch_youtube_videos(query=search_query, max_results=20, category_name=category)
    
    # 3. Merge (Avoid Duplicates)
    existing_ids = {v['id'] for v in _youtube_videos}
    added_count = 0
    for v in new_videos:
        if v['id'] not in existing_ids:
            _youtube_videos.append(v)
            existing_ids.add(v['id'])
            added_count += 1
            
    print(f"   ➕ Added {added_count} new videos to category '{category}'")
    
    return [v for v in _youtube_videos if v.get('category', '').lower() == category.lower()]


# ============ CHANNEL FETCHING ============
def fetch_channel_videos(channel_id, channel_title="Subscribed Channel", max_results=10):
    """Fetch latest videos from a specific channel."""
    client = get_youtube_client()
    if not client: return []

    try:
        print(f"[channel] Fetching videos for channel {channel_id} ({channel_title})...")
        request = client.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=max_results,
            order="date", # Get latest
            type="video"
        )
        response = request.execute()
        
        # Reuse existing parsing logic if possible, or simplified version here
        # We need to fetch details for duration check (Shorts filter)
        video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
        
        if not video_ids: return []
        
        vid_req = client.videos().list(
            part="snippet,contentDetails",
            id=",".join(video_ids)
        )
        vid_res = vid_req.execute()
        
        videos = []
        for item in vid_res.get("items", []):
            snippet = item["snippet"]
            content_details = item["contentDetails"]
            duration_iso = content_details.get("duration", "PT0S")
            
            duration_seconds = parse_duration(duration_iso)
            if duration_seconds <= 90: continue # Filter Shorts

            vid_id = item["id"]
            
            video = {
                "id": vid_id,
                "title": snippet["title"],
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url") or snippet["thumbnails"]["default"]["url"],
                "category": "Subscriptions", # Label them so they stand out or merge
                "duration": format_duration(duration_seconds),
                "tags": f"{snippet['title']}, {snippet.get('description', '')[:200]}",
                "description": snippet.get("description", "")[:500],
                "videoUrl": f"https://www.youtube.com/embed/{vid_id}",
                "channelTitle": snippet.get("channelTitle", channel_title),
                "channelId": snippet.get("channelId"),
                "channelThumbnail": "", 
                "publishedAt": snippet.get("publishedAt", "")
            }
            videos.append(video)
            
        # Add to Main Pool
        global _youtube_videos
        existing_ids = {v['id'] for v in _youtube_videos}
        added = 0
        for v in videos:
            if v['id'] not in existing_ids:
                _youtube_videos.append(v)
                existing_ids.add(v['id'])
                added += 1
                
        print(f"   [OK] Fetched {added} new videos from subscribed channel.")
        return videos

    except Exception as e:
        print(f"[ERROR] Error fetching channel videos: {e}")
        return []

# ============ PLAYLISTS ============
def add_to_playlist(user_id, playlist_name, video_id):
    """Add a video to a specific playlist."""
    global _playlists
    if user_id not in _playlists:
        _playlists[user_id] = {"Watch Later": []}
    
    if playlist_name not in _playlists[user_id]:
        _playlists[user_id][playlist_name] = []
    
    if video_id not in _playlists[user_id][playlist_name]:
        _playlists[user_id][playlist_name].append(video_id)
        return True
    return False

def remove_from_playlist(user_id, playlist_name, video_id):
    """Remove a video from a specific playlist."""
    global _playlists
    if user_id in _playlists and playlist_name in _playlists[user_id]:
        if video_id in _playlists[user_id][playlist_name]:
            _playlists[user_id][playlist_name].remove(video_id)
            return True
    return False

def get_user_playlists(user_id):
    """Get all playlists for a user."""
    return _playlists.get(user_id, {"Watch Later": []})

def get_playlist_videos(user_id, playlist_name):
    """Get all video details for a specific playlist."""
    vid_ids = _playlists.get(user_id, {}).get(playlist_name, [])
    videos = []
    for vid_id in vid_ids:
        v = get_video_by_id(vid_id)
        if v: videos.append(v)
    return videos

def get_liked_videos(user_id):
    """Get all videos liked by a user."""
    liked_list = []
    for vid_id, actions in _likes.items():
        if actions.get(user_id) is True:
            video = get_video_by_id(vid_id)
            if video:
                liked_list.append(video)
    return liked_list

def clear_liked_videos(user_id):
    """Clear all likes for a user."""
    # Note: mutating a dictionary does not require 'global'
    for vid_id in list(_likes.keys()):
        if user_id in _likes[vid_id]:
            _likes[vid_id].pop(user_id, None)
    return True

if __name__ == "__main__":

    print("Manual Sync Triggered")
    init_db()
    result = sync_youtube_to_db()
    print(f"Result: {result}")

