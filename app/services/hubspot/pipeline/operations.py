# app/services/hubspot/pipeline/operations.py

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.models.hubspot import HubSpotPipeline, HubSpotPipelineStage
from app.services.hubspot.utils.helpers import _handle_api_error

logger = logging.getLogger(__name__)


class PipelineOperations:
  def __init__(self, manager):
    self.manager = manager

  async def get_pipelines(self, object_type: str, archived: bool = False) -> List[HubSpotPipeline]:
    """Get pipelines for an object type."""
    try:
      # Check cache first
      cache_key = f"pipelines_{object_type}_{archived}"
      if cache_key in self.manager.pipelines_cache:
        logger.debug(f"Returning cached pipelines for {object_type}")
        return self.manager.pipelines_cache[cache_key]

      # Fetch from API
      api_response = await asyncio.to_thread(
          self.manager.client.crm.pipelines.pipelines_api.get_all,
          object_type=object_type,
          archived=archived
      )

      if api_response and api_response.results:
        pipelines = [
            HubSpotPipeline(**pipeline.to_dict())
            for pipeline in api_response.results
        ]

        # Cache the result
        self.manager.pipelines_cache[cache_key] = pipelines
        logger.info(
            f"Fetched and cached {len(pipelines)} pipelines for {object_type}")
        return pipelines
      else:
        logger.warning(f"No pipelines found for object type: {object_type}")
        return []

    except Exception as e:
      await _handle_api_error(e, f"get pipelines for {object_type}")
      return []

  async def get_pipeline_stages(self, pipeline_id: str, object_type: str, archived: bool = False) -> List[HubSpotPipelineStage]:
    """Get stages for a specific pipeline."""
    try:
      # Check cache first
      cache_key = f"stages_{object_type}_{pipeline_id}_{archived}"
      if cache_key in self.manager.stages_cache:
        logger.debug(f"Returning cached stages for pipeline {pipeline_id}")
        return self.manager.stages_cache[cache_key]

      # Get pipeline with stages
      api_response = await asyncio.to_thread(
          self.manager.client.crm.pipelines.pipelines_api.get_by_id,
          object_type=object_type,
          pipeline_id=pipeline_id,
          archived=archived
      )

      if api_response and hasattr(api_response, 'stages') and api_response.stages:
        stages = [
            HubSpotPipelineStage(**stage.to_dict())
            for stage in api_response.stages
        ]

        # Cache the result
        self.manager.stages_cache[cache_key] = stages
        logger.info(
            f"Fetched and cached {len(stages)} stages for pipeline {pipeline_id}")
        return stages
      else:
        logger.warning(f"No stages found for pipeline {pipeline_id}")
        return []

    except Exception as e:
      await _handle_api_error(e, f"get stages for pipeline {pipeline_id}")
      return []

  async def get_pipeline_by_id(self, pipeline_id: str, object_type: str) -> Optional[HubSpotPipeline]:
    """Get a specific pipeline by ID."""
    try:
      api_response = await asyncio.to_thread(
          self.manager.client.crm.pipelines.pipelines_api.get_by_id,
          object_type=object_type,
          pipeline_id=pipeline_id
      )

      if api_response:
        return HubSpotPipeline(**api_response.to_dict())
      else:
        logger.warning(
            f"Pipeline {pipeline_id} not found for object type: {object_type}")
        return None

    except Exception as e:
      await _handle_api_error(e, f"get pipeline {pipeline_id}")
      return None

  async def get_default_pipeline(self, object_type: str = "deals") -> Optional[HubSpotPipeline]:
    """Get the default pipeline for an object type."""
    try:
      pipelines = await self.get_pipelines(object_type)
      if pipelines:
        # Look for default pipeline or return the first one
        default_pipeline = next(
            (p for p in pipelines if getattr(p, 'default', False)),
            pipelines[0]
        )
        return default_pipeline
      return None
    except Exception as e:
      await _handle_api_error(e, f"get default pipeline for {object_type}")
      return None
