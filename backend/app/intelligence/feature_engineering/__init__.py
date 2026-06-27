"""Feature-engineering modules and the pipeline that composes them.

Each submodule exposes pure functions that consume a `Candidate` and
return either a scalar feature or a small structured value. The
`FeaturePipeline` glues them into a `CandidateFeatures` aggregate.
"""

from app.intelligence.feature_engineering.pipeline import FeaturePipeline

__all__ = ["FeaturePipeline"]
