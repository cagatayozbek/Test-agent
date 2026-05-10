"""Built-in metrics.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import six
from . import backend as K
# stubbed: from .losses import mean_squared_error
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
mean_squared_error = _Stub()
# stubbed: from .losses import mean_absolute_error
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
mean_absolute_error = _Stub()
# stubbed: from .losses import mean_absolute_percentage_error
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
mean_absolute_percentage_error = _Stub()
# stubbed: from .losses import mean_squared_logarithmic_error
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
mean_squared_logarithmic_error = _Stub()
# stubbed: from .losses import hinge
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
hinge = _Stub()
# stubbed: from .losses import logcosh
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
logcosh = _Stub()
# stubbed: from .losses import squared_hinge
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
squared_hinge = _Stub()
# stubbed: from .losses import categorical_crossentropy
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
categorical_crossentropy = _Stub()
# stubbed: from .losses import sparse_categorical_crossentropy
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
sparse_categorical_crossentropy = _Stub()
# stubbed: from .losses import binary_crossentropy
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
binary_crossentropy = _Stub()
# stubbed: from .losses import kullback_leibler_divergence
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
kullback_leibler_divergence = _Stub()
# stubbed: from .losses import poisson
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
poisson = _Stub()
# stubbed: from .losses import cosine_proximity
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
cosine_proximity = _Stub()
# stubbed: from .utils.generic_utils import deserialize_keras_object
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
deserialize_keras_object = _Stub()
# stubbed: from .utils.generic_utils import serialize_keras_object
class _Stub: __getattr__ = lambda self, n: _Stub(); __call__ = lambda self, *a, **k: _Stub()
serialize_keras_object = _Stub()


def binary_accuracy(y_true, y_pred):
    return K.mean(K.equal(y_true, K.round(y_pred)), axis=-1)


def categorical_accuracy(y_true, y_pred):
    return K.cast(K.equal(K.argmax(y_true, axis=-1),
                          K.argmax(y_pred, axis=-1)),
                  K.floatx())


def sparse_categorical_accuracy(y_true, y_pred):
    # flatten y_true in case it's in shape (num_samples, 1) instead of (num_samples,)
    return K.cast(K.equal(K.flatten(y_true),
                          K.cast(K.argmax(y_pred, axis=-1), K.floatx())),
                  K.floatx())


def top_k_categorical_accuracy(y_true, y_pred, k=5):
    return K.mean(K.in_top_k(y_pred, K.argmax(y_true, axis=-1), k), axis=-1)


def sparse_top_k_categorical_accuracy(y_true, y_pred, k=5):
    return K.mean(K.in_top_k(y_pred, K.cast(K.max(y_true, axis=-1), 'int32'), k), axis=-1)


# Aliases

mse = MSE = mean_squared_error
mae = MAE = mean_absolute_error
mape = MAPE = mean_absolute_percentage_error
msle = MSLE = mean_squared_logarithmic_error
cosine = cosine_proximity


def serialize(metric):
    return serialize_keras_object(metric)


def deserialize(config, custom_objects=None):
    return deserialize_keras_object(config,
                                    module_objects=globals(),
                                    custom_objects=custom_objects,
                                    printable_module_name='metric function')


def get(identifier):
    if isinstance(identifier, dict):
        config = {'class_name': str(identifier), 'config': {}}
        return deserialize(config)
    elif isinstance(identifier, six.string_types):
        return deserialize(str(identifier))
    elif callable(identifier):
        return identifier
    else:
        raise ValueError('Could not interpret '
                         'metric function identifier:', identifier)