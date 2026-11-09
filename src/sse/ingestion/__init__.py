"""Strategic Systems Engine - Ingestion Package.

Provides observation validation, confidence decay tracking, provenance checking,
and multi-source conflict reconciliation.
"""

from sse.ingestion.matrix_compressor import (
    ActionClusterMapping,
    CompressedMatrixResult,
    MatrixCompressor,
)
from sse.ingestion.payoff_formulator import (
    ContinuousPayoffFormulator,
    DiscretizationScheme,
    RiskPreferences,
)
from sse.ingestion.reconciler import ObservationReconciler
from sse.ingestion.validator import ObservationValidator

__all__ = [
    "ActionClusterMapping",
    "CompressedMatrixResult",
    "ContinuousPayoffFormulator",
    "DiscretizationScheme",
    "MatrixCompressor",
    "ObservationReconciler",
    "ObservationValidator",
    "RiskPreferences",
]

