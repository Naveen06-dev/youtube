"""
Custom TensorFlow layers for the Deep YouTube Recommendation model.
These layers are required to load the trained candidate_generation.h5 model.
"""
import tensorflow as tf

class MaskedEmbeddingsAggregatorLayer(tf.keras.layers.Layer):
    """Aggregates masked embeddings using sum or mean."""
    def __init__(self, agg_mode='sum', **kwargs):
        super(MaskedEmbeddingsAggregatorLayer, self).__init__(**kwargs)
        if agg_mode not in ['sum', 'mean']:
            raise NotImplementedError('mode {} not implemented!'.format(agg_mode))
        self.agg_mode = agg_mode
        self.supports_masking = True
    
    @tf.function
    def call(self, inputs, mask=None):
        if mask is None:
            return tf.reduce_sum(inputs, axis=1) if self.agg_mode == 'sum' else tf.reduce_mean(inputs, axis=1)
        
        # Safe masking: cast mask to float and multiply
        mask_expanded = tf.expand_dims(tf.cast(mask, inputs.dtype), -1)
        masked_inputs = inputs * mask_expanded
        
        if self.agg_mode == 'sum':
            aggregated = tf.reduce_sum(masked_inputs, axis=1)
        elif self.agg_mode == 'mean':
            valid_count = tf.reduce_sum(mask_expanded, axis=1)
            valid_count = tf.maximum(valid_count, 1e-7)
            aggregated = tf.reduce_sum(masked_inputs, axis=1) / valid_count
            
        return aggregated

    def get_config(self):
        return {'agg_mode': self.agg_mode}

class L2NormLayer(tf.keras.layers.Layer):
    """L2 normalization layer."""
    def __init__(self, **kwargs):
        super(L2NormLayer, self).__init__(**kwargs)
        self.supports_masking = True
    
    @tf.function
    def call(self, inputs, mask=None):
        # Simply normalize. Masking handled by aggregator or embedding.
        return tf.math.l2_normalize(inputs, axis=-1)

    def compute_mask(self, inputs, mask=None):
        return mask
