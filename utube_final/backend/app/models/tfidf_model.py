import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.database.db import get_all_videos

class Recommender:
    def __init__(self):
        self.refresh_data()
        
    def refresh_data(self):
        """Fetch latest data from DB and retrain vectorizer"""
        self.data = get_all_videos()
        self.df = pd.DataFrame(self.data)
        
        if self.df.empty:
            print("Warning: Database is empty. Recommendations will not work.")
            self.tfidf_matrix = None
            return

        self.vectorizer = TfidfVectorizer(stop_words='english')
        # Combine distinct features for better matching
        self.df['combined_features'] = (
            self.df['title'].fillna('') + " " + 
            self.df['category'].fillna('') + " " + 
            self.df['tags'].fillna('')
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df['combined_features'])
        
    def get_recommendations(self, video_id: str, user_id: str = None, top_n: int = 50):
        try:
            if self.tfidf_matrix is None:
                return []

            # 1. Content-Based Score (Cosine Similarity)
            idx_list = self.df.index[self.df['id'] == video_id].tolist()
            if not idx_list:
                 return self.df.head(top_n).to_dict('records')
            
            idx = idx_list[0]
            cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
            sim_scores = cosine_sim[idx] # Array of scores for all videos

            # 2. User Interest Score (Behavioral)
            # Boost videos that match categories the user has interacted with
            user_interest_scores = [0] * len(self.df)
            if user_id:
                from app.database.db import get_user_history
                history = get_user_history(user_id)
                # Count frequency of categories in history
                clicked_ids = [h['video_id'] for h in history]
                clicked_metas = self.df[self.df['id'].isin(clicked_ids)]
                if not clicked_metas.empty:
                    fav_categories = clicked_metas['category'].value_counts(normalize=True).to_dict()
                    
                    # Assign scores
                    for i, row in self.df.iterrows():
                        cat = row['category']
                        # Boost score by the % frequency of this category in user history
                        user_interest_scores[i] = fav_categories.get(cat, 0)

            # 3. Popularity Score (Simple heuristic based on tags/views length as proxy if real views missing)
            # In a real app, we would use normalized 'viewCount'
            # Here we just give a small random boost or use index proxy to simulate "trending"
            import numpy as np
            popularity_scores = np.linspace(0.1, 0, len(self.df)) # Slight bias to newer/top items

            # 4. Final Weighted Hybrid Score
            # Weights: Content (60%), User History (30%), Popularity (10%)
            final_scores = []
            for i in range(len(self.df)):
                if i == idx: continue # Skip self
                
                # Combine scores and handle NaNs/Overflows
                score = (sim_scores[i] * 0.6) + (user_interest_scores[i] * 0.3) + (popularity_scores[i] * 0.1)
                
                # Ensure JSON compliance (No NaN/Inf)
                if np.isnan(score) or np.isinf(score):
                    score = 0.0
                
                final_scores.append((i, float(score)))

            # Sort
            final_scores = sorted(final_scores, key=lambda x: x[1], reverse=True)
            final_scores = final_scores[:top_n]
            
            video_indices = [i[0] for i in final_scores]
            recommendations = self.df.iloc[video_indices].to_dict('records')
            
            # Additional JSON sanitization for the final dict
            for r in recommendations:
                for k, v in r.items():
                    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                        r[k] = 0.0
            
            if len(recommendations) < 5:
                 fill = self.df[~self.df['id'].isin([r['id'] for r in recommendations] + [video_id])].head(top_n - len(recommendations))
                 recommendations.extend(fill.to_dict('records'))
                 
            return recommendations
        except Exception as e:
            print(f"Error in recommendation: {e}")
            return []
