# app/services/hubspot/association/operations.py

import asyncio
import logging
from typing import Any, Dict, List, Optional

from hubspot.crm.associations.v4.models import (
    AssociationSpec,
    PublicObjectId,
    BatchInputPublicAssociationMultiPost,
    PublicAssociationMultiPost,
)

from app.services.hubspot.utils.helpers import _handle_api_error

logger = logging.getLogger(__name__)


class AssociationOperations:
  def __init__(self, manager):
    self.manager = manager

  async def associate_objects(
      self,
      from_object_type: str,
      from_object_id: str,
      to_object_type: str,
      to_object_id: str,
      association_type_id: int,
      association_category: str = "HUBSPOT_DEFINED"
  ) -> bool:
    """
    Associates two HubSpot objects using the v4 Associations API.

    Args:
        from_object_type: The source object type (e.g., "leads", "contacts", "companies")
        from_object_id: The ID of the source object
        to_object_type: The target object type (e.g., "contacts", "companies")
        to_object_id: The ID of the target object
        association_type_id: The numeric ID of the association type
        association_category: Either "HUBSPOT_DEFINED" or "USER_DEFINED"

    Returns:
        Boolean indicating success or failure
    """
    context = f"associating {from_object_type} {from_object_id} to {to_object_type} {to_object_id} (type {association_type_id})"
    logger.debug(f"Attempting to {context}")

    # Convert plural input object types to singular lowercase for v4 API calls
    sdk_from_object_type = self._normalize_object_type(from_object_type)
    sdk_to_object_type = self._normalize_object_type(to_object_type)

    try:
      # Prepare the request payload following v4 Associations API format
      association_payload = [
          {
              "associationCategory": association_category,
              "associationTypeId": int(association_type_id)
          }
      ]

      # Create from/to object IDs
      from_object = PublicObjectId(id=from_object_id)
      to_object = PublicObjectId(id=to_object_id)

      # Create the association post object
      association = PublicAssociationMultiPost(
          _from=from_object,
          to=to_object,
          types=association_payload
      )

      # Create batch input for the association
      batch_input = BatchInputPublicAssociationMultiPost(inputs=[association])

      # Call the API
      await asyncio.to_thread(
          self.manager.client.crm.associations.v4.batch_api.create,
          from_object_type=sdk_from_object_type,
          to_object_type=sdk_to_object_type,
          batch_input_public_association_multi_post=batch_input
      )

      logger.info(f"Successfully {context}")
      return True
    except Exception as e:
      logger.error(f"Error {context}: {e}", exc_info=True)
      return False

  async def batch_associate_objects(
      self,
      from_object_type: str,
      from_object_id: str,
      to_object_type: str,
      to_object_ids: List[str],
      association_type_id: int,
      association_category: str = "HUBSPOT_DEFINED"
  ) -> bool:
    """
    Associates one object with multiple objects in batch using v4 Associations API.

    Args:
        from_object_type: The source object type
        from_object_id: The ID of the source object
        to_object_type: The target object type
        to_object_ids: List of IDs of the target objects
        association_type_id: The numeric ID of the association type
        association_category: Either "HUBSPOT_DEFINED" or "USER_DEFINED"

    Returns:
        Boolean indicating success or failure
    """
    context = f"batch associating {from_object_type} {from_object_id} to {len(to_object_ids)} {to_object_type} (type {association_type_id})"
    logger.debug(f"Attempting to {context}")

    if not to_object_ids:
      logger.warning(
          f"No target objects to associate with {from_object_type} {from_object_id}")
      return True

    # Convert plural input object types to singular lowercase for v4 API calls
    sdk_from_object_type = self._normalize_object_type(from_object_type)
    sdk_to_object_type = self._normalize_object_type(to_object_type)

    try:
      # Prepare the association type for all associations
      association_payload = [
          {
              "associationCategory": association_category,
              "associationTypeId": int(association_type_id)
          }
      ]

      # Create association inputs for each target object
      associations = []
      for to_id in to_object_ids:
        from_object = PublicObjectId(id=from_object_id)
        to_object = PublicObjectId(id=to_id)

        associations.append(
            PublicAssociationMultiPost(
                _from=from_object,
                to=to_object,
                types=association_payload
            )
        )

      # Create batch input for associations
      batch_input = BatchInputPublicAssociationMultiPost(inputs=associations)

      # Call the API
      await asyncio.to_thread(
          self.manager.client.crm.associations.v4.batch_api.create,
          from_object_type=sdk_from_object_type,
          to_object_type=sdk_to_object_type,
          batch_input_public_association_multi_post=batch_input
      )

      logger.info(f"Successfully {context}")
      return True
    except Exception as e:
      logger.error(f"Error {context}: {e}", exc_info=True)
      return False

  def _normalize_object_type(self, object_type: str) -> str:
    """Convert plural object types to singular lowercase for API calls."""
    sdk_object_type = object_type.lower()
    if sdk_object_type == "contacts":
      sdk_object_type = "contact"
    elif sdk_object_type == "companies":
      sdk_object_type = "company"
    elif sdk_object_type == "deals":
      sdk_object_type = "deal"
    elif sdk_object_type == "tickets":
      sdk_object_type = "ticket"
    elif sdk_object_type.endswith('s'):
      sdk_object_type = sdk_object_type[:-1]
    return sdk_object_type
