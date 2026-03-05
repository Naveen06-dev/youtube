"""
Configuration for the Deep Learning Recommendation Model.
These values must match the training configuration.
"""

# Model Architecture Config
EMBEDDING_DIMS = 16
DENSE_UNITS = 64
DROPOUT_PCT = 0.0
ALPHA = 0.0
NUM_CLASSES = 11
LEARNING_RATE = 0.003

# Inference Config
MAX_SEQUENCE_LENGTH = 50  # Maximum length of watch/search history sequences
TOP_K_CANDIDATES = 100    # Number of candidates to generate
