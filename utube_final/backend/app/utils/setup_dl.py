"""
Setup script for Deep Learning Recommendation Engine Integration.

Run this script to verify your setup and get instructions.
"""

import os
import sys

def setup_deep_learning():
    """Verify setup and provide instructions."""
    
    # Paths
    target_model = os.path.join(os.path.dirname(__file__), "candidate_generation.h5")
    
    print("=" * 60)
    print("🚀 Deep Learning Recommendation Engine Setup")
    print("=" * 60)
    
    # Step 1: Check if model file exists
    print(f"\n📦 Checking for trained model...")
    print(f"   Looking for: {target_model}")
    
    if os.path.exists(target_model):
        print("   ✅ Model file found!")
    else:
        print("   ⚠️ Model file not found!")
        print("\n   Please copy the trained model manually:")
        print("   ─────────────────────────────────────────")
        print("   SOURCE: Deep-Youtube-Recommendations-master\\candidate_generation.h5")
        print(f"   TARGET: {target_model}")
        print("   ─────────────────────────────────────────")
        return False
    
    # Step 2: Verify TensorFlow installation
    print("\n📦 Checking TensorFlow installation...")
    try:
        import tensorflow as tf
        print(f"   ✅ TensorFlow {tf.__version__} is installed")
    except ImportError:
        print("   ⚠️ TensorFlow not found. Installing...")
        os.system(f"{sys.executable} -m pip install tensorflow>=2.10.0")
        print("   ✅ TensorFlow installed!")
    
    # Step 3: Verify model can be loaded
    print("\n🔍 Testing model load...")
    try:
        from dl_layers import MaskedEmbeddingsAggregatorLayer, L2NormLayer
        import tensorflow as tf
        
        custom_objects = {
            'MaskedEmbeddingsAggregatorLayer': MaskedEmbeddingsAggregatorLayer,
            'L2NormLayer': L2NormLayer
        }
        
        model = tf.keras.models.load_model(
            target_model, 
            custom_objects=custom_objects,
            compile=False
        )
        print(f"   ✅ Model loaded successfully!")
        print(f"   📊 Model inputs: {[i.name for i in model.inputs]}")
        print(f"   📊 Model outputs: {[o.name for o in model.outputs]}")
    except Exception as e:
        print(f"   ❌ Error loading model: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Setup complete! You can now run the server:")
    print("   uvicorn main:app --reload")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = setup_deep_learning()
    sys.exit(0 if success else 1)

