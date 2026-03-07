import re
import random
from datetime import datetime

class SmartRankingEngine:
    """
    High-Performance Video Ranking System.
    Implements Intent Detection, Personalization, Engagement Signals, and Diversity.
    """

    def __init__(self, user_profile=None, global_stats=None):
        self.user_profile = user_profile or {}
        self.global_stats = global_stats or {}
        
        # Simple synonym map for "Query Understanding"
        self.synonyms = {
            "ai": "artificial intelligence",
            "ml": "machine learning",
            "coding": "programming",
            "reactjs": "react",
            "youtube": "video"
        }

    def _detect_intent(self, query):
        """Rule 1: Detect intent based on query keywords."""
        query = query.lower()
        if any(w in query for w in ["how to", "tutorial", "learn", "course"]):
            return "educational"
        if any(w in query for w in ["news", "update", "latest", "today"]):
            return "news"
        if any(w in query for w in ["song", "music", "lyrics", "official video"]):
            return "music"
        if any(w in query for w in ["highlights", "game", "match", "sports"]):
            return "sports"
        return "general"

    def _process_query(self, query):
        """Rule 1: Query Understanding & Expansion."""
        query = query.lower().strip()
        # Expand synonyms
        for word, expansion in self.synonyms.items():
            if f" {word} " in f" {query} " or query == word:
                query = query.replace(word, expansion)
        return query

    def _calculate_score(self, video, processed_query, intent):
        score = 0
        title = video.get("title", "").lower()
        description = video.get("description", "").lower()
        channel_title = video.get("channelTitle", "").lower()
        
        # --- 2. RELEVANCE SCORING ---
        # Exact keyword match in title (Highest weight)
        if processed_query in title:
            score += 1000
        
        # Parts of query in title
        query_terms = processed_query.split()
        matches = sum(1 for term in query_terms if term in title)
        score += matches * 150
        
        # Channel match
        if processed_query in channel_title:
            score += 500
            
        # Intent matching
        video_category = video.get("category", "General").lower()
        if intent == "educational" and any(k in title for k in ["how", "tutorial", "guide"]):
            score += 300
        elif intent == video_category:
            score += 200

        # --- 3. PERSONALIZATION & HISTORY (CRITICAL) ---
        # 3a. Liked Categories Boost
        liked_cats = [c.lower() for c in self.user_profile.get("liked_categories", [])]
        if video_category in liked_cats:
            score += 2000 # Massive boost to ensure history relevance
            
        # 3b. Interest Overlap (if no query match)
        # If the user is on 'Recommended' feed, we check overlap with history topics
        interest_topics = self.user_profile.get("interest_topics", [])
        has_interest_match = False
        for topic in interest_topics:
            if topic.lower() in title or topic.lower() in video.get('tags', '').lower():
                score += 1500
                has_interest_match = True
        
        # 3c. Strict Filtering: If user has history but this video matches NOTHING, penalize heavily
        # This ensures the "ONLY relevant" requirement
        if interest_topics or liked_cats:
             if not has_interest_match and video_category not in liked_cats and processed_query == "recommended":
                 score -= 5000 # Bury unrelated content

        # Subscribed channels boost
        subs = self.user_profile.get("subscribed_channels", [])
        if video.get("channelId") in subs or video.get("channelTitle") in subs:
            score += 400
            
        # Watch history penalty (reduce already watched)
        history = self.user_profile.get("watch_history", [])
        if video.get("id") in history:
            score -= 800 # Stronger reduction to keep feed fresh

        # --- 4. ENGAGEMENT SIGNALS (Simulated if missing) ---
        # Only add a small boost from engagement so it doesn't override history
        ctr = video.get("ctr", random.uniform(0.01, 0.15))
        score += ctr * 500
        
        # --- 5. FRESHNESS ---
        try:
            pub_date_str = video.get("publishedAt", "")
            if pub_date_str:
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                days_old = (datetime.now(pub_date.tzinfo) - pub_date).days
                if days_old < 30:
                    score += 200 # Recent boost
        except:
            pass

        return score

    def rank(self, candidates, user_query, top_n=10):
        """
        Rank a list of candidate videos based on the sophisticated logic.
        """
        processed_query = self._process_query(user_query)
        intent = self._detect_intent(user_query)
        
        scored_vids = []
        for v in candidates:
            final_score = self._calculate_score(v, processed_query, intent)
            scored_vids.append({
                "video": v,
                "relevance_score": round(final_score, 2),
                "debug_signals": {
                    "intent": intent,
                    "ctr": round(v.get("ctr", random.uniform(0.02, 0.12)), 3)
                }
            })
            
        # Initial Sort
        scored_vids.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # --- 6. DIVERSITY ---
        # Avoid showing too many from same channel
        channel_counts = {}
        final_rank = []
        
        for item in scored_vids:
            channel = item["video"].get("channelTitle", "Unknown")
            count = channel_counts.get(channel, 0)
            
            if count >= 2: # Max 2 from same channel in top results
                item["relevance_score"] -= 400
            
            channel_counts[channel] = count + 1
            final_rank.append(item)

        # Final Sort after diversity penalty
        final_rank.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Return in JSON format - ENRICHED WITH FULL VIDEO DATA
        # Frontend expects full video objects (thumbnail, URL, etc.)
        output = []
        for i, item in enumerate(final_rank[:top_n]):
            v = item["video"].copy() # Work on a copy to avoid side effects
            # Inject ranking metadata for debugging/UI use
            v["rank"] = i + 1
            v["relevance_score"] = item["relevance_score"]
            output.append(v)
            
        return output
