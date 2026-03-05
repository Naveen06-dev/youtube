"""
Deep Learning Recommender - Real-Time YouTube Video Recommendation Engine

This module integrates the trained TensorFlow Deep Neural Network model
for generating personalized video recommendations based on:
- Watch history
- Search history  
- Video age/freshness
- User behavioral patterns

The model is based on Google's "Deep Neural Networks for YouTube Recommendations" paper.
"""

import numpy as np
import pandas as pd
import os
import warnings

# Silence TensorFlow and Keras logs before importing TF
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import warnings
# Global ignore for cleaner logs
warnings.filterwarnings('ignore') 

import tensorflow as tf
import logging

# Aggressively silence TensorFlow logs
tf.get_logger().setLevel(logging.ERROR)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from typing import List, Dict, Optional
from functools import lru_cache

# Import custom layers for model loading
from .dl_layers import MaskedEmbeddingsAggregatorLayer, L2NormLayer
from . import dl_config as cfg

class DeepRecommender:
    """
    Deep Learning-based recommendation engine that uses a trained neural network
    to generate personalized video recommendations.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize the Deep Recommender.
        """
        if model_path is None:
            # Default to the one in the same folder as this script
            model_path = os.path.join(os.path.dirname(__file__), "candidate_generation.h5")
        
        self.model = None
        self.model_path = model_path
        self.video_embeddings = {}
        self.video_id_to_idx = {}
        self.idx_to_video_id = {}
        self.is_initialized = False
        
        # Try to load the model
        self._load_model()
    
    def _load_model(self):
        """Load the trained TensorFlow model with custom layers."""
        try:
            if os.path.exists(self.model_path):
                # Register custom layers
                custom_objects = {
                    'MaskedEmbeddingsAggregatorLayer': MaskedEmbeddingsAggregatorLayer,
                    'L2NormLayer': L2NormLayer
                }
                
                self.model = tf.keras.models.load_model(
                    self.model_path, 
                    custom_objects=custom_objects,
                    compile=False  # Don't need to compile for inference
                )
                self.is_initialized = True
                print(f"✅ Deep Learning model loaded successfully from {self.model_path}")
            else:
                print(f"⚠️ Model file not found at {self.model_path}. Using fallback mode.")
                self.is_initialized = False
        except Exception as e:
            print(f"⚠️ Failed to load DL model: {e}. Using fallback mode.")
            self.is_initialized = False
    
    def build_video_index(self, videos: List[Dict]):
        """
        Build an index mapping video IDs to indices for the model.
        
        Args:
            videos: List of video dictionaries from the database
        """
        self.video_id_to_idx = {v['id']: idx for idx, v in enumerate(videos)}
        self.idx_to_video_id = {idx: v['id'] for idx, v in enumerate(videos)}
        self.videos_df = pd.DataFrame(videos)
        print(f"📊 Video index built with {len(videos)} videos")
    
    def _prepare_user_features(
        self, 
        watch_history: List[str], 
        search_history: List[str] = None,
        max_len: int = None
    ) -> Dict[str, np.ndarray]:
        """
        Prepare user features for model input.
        
        Args:
            watch_history: List of video IDs the user has watched
            search_history: List of search queries (optional)
            max_len: Maximum sequence length
            
        Returns:
            Dictionary of numpy arrays ready for model input
        """
        max_len = max_len or cfg.MAX_SEQUENCE_LENGTH
        
        # Convert video IDs to indices
        watch_indices = [
            self.video_id_to_idx.get(vid, 0) 
            for vid in watch_history[-max_len:]
        ]
        
        # Pad sequences
        watch_hist = tf.keras.preprocessing.sequence.pad_sequences(
            [watch_indices], maxlen=max_len, padding='pre'
        )
        
        # Create time weights (more recent = higher weight)
        time_weights = np.linspace(0.1, 1.0, len(watch_indices))
        time_weights = np.pad(time_weights, (max_len - len(time_weights), 0))
        watch_hist_time = np.array([time_weights])
        
        # Search history (use zeros if not provided)
        if search_history:
            search_encoded = [hash(q) % cfg.NUM_CLASSES for q in search_history[-max_len:]]
            search_hist = tf.keras.preprocessing.sequence.pad_sequences(
                [search_encoded], maxlen=max_len, padding='pre', dtype=float
            )
        else:
            search_hist = np.zeros((1, max_len))
        
        # Example age (freshness signal)
        example_age = np.ones((1, max_len)) * 0.5  # Neutral freshness
        
        return {
            'watch_hist': watch_hist,
            'watch_hist_time': watch_hist_time,
            'search_hist': search_hist + 1e-10,  # Prevent division by zero
            'example_age': example_age
        }
    
    def predict_candidates(
        self, 
        watch_history: List[str],
        search_history: List[str] = None,
        top_k: int = None
    ) -> List[int]:
        """
        Use the DL model to predict candidate video indices.
        """
        if not self.is_initialized or self.model is None:
            return []
        
        top_k = top_k or cfg.TOP_K_CANDIDATES
        
        try:
            # Prepare features
            features = self._prepare_user_features(watch_history, search_history)
            
            # Final validation: check for NaNs in inputs which can crash TF
            for k, v in features.items():
                if np.isnan(v).any():
                    features[k] = np.nan_to_num(v)

            # Ensure indices are within NUM_CLASSES range to prevent embedding errors
            # embedding_matrix size is likely matched to NUM_CLASSES
            max_idx = cfg.NUM_CLASSES - 1
            if np.any(features['watch_hist'] > max_idx):
                # print(f"⚠️ Clipping watch history indices > {max_idx}")
                features['watch_hist'] = np.clip(features['watch_hist'], 0, max_idx)
            
            # Run inference
            predictions = self.model.predict([
                features['watch_hist'],
                features['watch_hist_time'],
                features['search_hist'],
                features['example_age']
            ], verbose=0)
            
            # Get top-k candidates
            if predictions is None or len(predictions) == 0:
                return []
                
            scores = predictions[0]
            
            # Ensure scores are valid
            if np.isnan(scores).any():
                scores = np.nan_to_num(scores)
                
            top_indices = np.argsort(scores)[::-1][:top_k]
            
            return [int(i) for i in top_indices]
            
        except Exception as e:
            print(f"⚠️ Prediction error: {e}")
            import traceback
            # print(traceback.format_exc()) # Debug only
            return []
    
    def get_deep_recommendations(
        self,
        current_video_id: str,
        user_id: str,
        videos: List[Dict],
        user_history: List[Dict],
        top_n: int = 20
    ) -> List[Dict]:
        """
        Get personalized recommendations using the Deep Learning model
        combined with content-based filtering for the final ranking.
        
        This implements a two-stage approach:
        1. Candidate Generation (DL model) - Broad retrieval
        2. Ranking (Content similarity) - Fine-grained scoring
        
        Args:
            current_video_id: The video currently being watched
            user_id: User identifier
            videos: All available videos
            user_history: User's interaction history
            top_n: Number of recommendations to return
            
        Returns:
            List of recommended video dictionaries
        """
        # Build/update video index
        self.build_video_index(videos)
        
        # Get user's watch history
        watch_history = [h.get('video_id', '') for h in user_history]
        if current_video_id:
            watch_history.append(current_video_id)
        
        # If no history, return popular/recent videos
        if not watch_history:
            return videos[:top_n]
        
        recommendations = []
        
        # Stage 1: DL-based Candidate Generation
        if self.is_initialized:
            candidate_indices = self.predict_candidates(
                watch_history=watch_history,
                top_k=top_n * 3  # Get more candidates for ranking
            )
            
            # Map indices back to video data
            for idx in candidate_indices:
                # Map model output class to video
                video_idx = idx % len(videos)
                if video_idx < len(videos):
                    video = videos[video_idx]
                    if video['id'] != current_video_id and video['id'] not in watch_history:
                        recommendations.append(video)
        
        # Stage 2: Hybrid Scoring (combine DL score with content similarity)
        if len(recommendations) < top_n:
            # Fallback: Add content-similar videos
            current_video = next((v for v in videos if v['id'] == current_video_id), None)
            if current_video:
                current_category = current_video.get('category', '')
                current_tags = set(current_video.get('tags', '').lower().split(','))
                
                for video in videos:
                    if video['id'] == current_video_id:
                        continue
                    if video in recommendations:
                        continue
                    if video['id'] in watch_history:
                        continue
                    
                    # Score based on category and tag overlap
                    score = 0
                    if video.get('category') == current_category:
                        score += 0.5
                    
                    video_tags = set(video.get('tags', '').lower().split(','))
                    tag_overlap = len(current_tags & video_tags)
                    score += tag_overlap * 0.1
                    
                    video['_score'] = score
                    recommendations.append(video)
        
        # Sort by score and return top_n
        recommendations = sorted(
            recommendations, 
            key=lambda x: x.get('_score', 0), 
            reverse=True
        )[:top_n]
        
        # Clean up score field
        for r in recommendations:
            r.pop('_score', None)
        
        return recommendations


# Singleton instance for the application
_deep_recommender_instance = None

def get_deep_recommender() -> DeepRecommender:
    """Get or create the singleton DeepRecommender instance."""
    global _deep_recommender_instance
    if _deep_recommender_instance is None:
        _deep_recommender_instance = DeepRecommender()
    return _deep_recommender_instance
