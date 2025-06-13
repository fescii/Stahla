from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from enum import Enum


class ServiceType(str, Enum):
  """Enum for supported service types."""
  QUOTE = "quote"
  LOCATION = "location"
  GMAPS = "gmaps"
  REDIS = "redis"


class LatencyStatus(str, Enum):
  """Enum for latency status levels."""
  GOOD = "good"
  WARNING = "warning"
  CRITICAL = "critical"
  UNKNOWN = "unknown"
  ERROR = "error"


class ServicePercentiles(BaseModel):
  """Percentile metrics for a single service."""
  service_type: ServiceType
  p50: Optional[float] = Field(
      None, description="50th percentile latency in ms")
  p90: Optional[float] = Field(
      None, description="90th percentile latency in ms")
  p95: Optional[float] = Field(
      None, description="95th percentile latency in ms")
  p99: Optional[float] = Field(
      None, description="99th percentile latency in ms")
  sample_count: int = Field(
      0, description="Number of samples used for calculation")
  status: LatencyStatus = Field(
      LatencyStatus.UNKNOWN, description="Status based on P95 threshold")
  last_updated: Optional[datetime] = Field(
      None, description="When these metrics were last calculated")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }
