# app/services/hubspot_service.py

import hubspot
from hubspot.crm.contacts import SimplePublicObjectInput, ApiException as ContactsApiException
from hubspot.crm.deals import SimplePublicObjectInput as DealSimplePublicObjectInput, ApiException as DealsApiException
import logfire
from typing import Optional

# Import settings and models
from app.core.config import settings
from app.models.hubspot_models import (
	HubSpotContactInput,
	HubSpotDealInput,
	HubSpotApiResult,
	HubSpotContactResult, # For potential return type hinting
	HubSpotDealResult # For potential return type hinting
)

class HubSpotManager:
	"""
	Manages interactions with the HubSpot API using the official client library.
	Handles creation and updates for Contacts and Deals.
	"""
	
	def __init__(self):
		"""Initializes the HubSpot client using the API key from settings."""
		try:
			# Initialize the official HubSpot client
			self.client = hubspot.Client.create(api_key=settings.HUBSPOT_API_KEY)
			logfire.info("HubSpot client initialized successfully.")
		except Exception as e:
			logfire.error(f"Failed to initialize HubSpot client: {e}", exc_info=True)
			# Depending on requirements, you might want to raise this exception
			# or handle it gracefully so the app can start but HubSpot features fail.
			self.client = None # Ensure client is None if init fails
	
	def _handle_api_exception(self, e: Exception, operation: str, entity_type: str, entity_data: Optional[dict] = None) -> HubSpotApiResult:
		"""Handles common logging and result formatting for API exceptions."""
		error_message = f"HubSpot API Error during {operation} {entity_type}"
		if hasattr(e, 'body'): # HubSpot ApiException often has details in body
			error_message += f": {e.body}"
		else:
			error_message += f": {e}"
		
		logfire.error(
			error_message,
			exc_info=True,
			operation=operation,
			entity_type=entity_type,
			entity_data=entity_data # Log input data for context if available
		)
		return HubSpotApiResult(
			status="error",
			entity_type=entity_type,
			message=error_message,
			details=str(e) # Or e.body if available
		)
	
	def search_contact_by_email(self, email: str) -> Optional[str]:
		"""
		Searches for a HubSpot contact by email.
		Returns the contact ID if found, otherwise None.
		"""
		if not self.client:
			logfire.error("HubSpot client not initialized. Cannot search contact.")
			return None
		
		try:
			# Define search request
			search_request = hubspot.crm.contacts.PublicObjectSearchRequest(
				filter_groups=[
					{
						"filters": [
							{
								"propertyName": "email",
								"operator": "EQ",
								"value": email
							}
						]
					}
				],
				properties=["email", "firstname", "lastname"], # Request specific properties
				limit=1 # We only need one match
			)
			# Execute the search
			logfire.debug(f"Searching HubSpot contact by email: {email}")
			search_results = self.client.crm.contacts.search_api.do_search(
				public_object_search_request=search_request
			)
			
			if search_results.total > 0 and search_results.results:
				contact_id = search_results.results[0].id
				logfire.info(f"Found existing HubSpot contact ID {contact_id} for email {email}")
				return contact_id
			else:
				logfire.info(f"No existing HubSpot contact found for email {email}")
				return None
		
		except ContactsApiException as e:
			self._handle_api_exception(e, "search", "contact", entity_data={"email": email})
			return None
		except Exception as e: # Catch other potential errors
			self._handle_api_exception(e, "search", "contact", entity_data={"email": email})
			return None
	
	
	def create_or_update_contact(self, contact_input: HubSpotContactInput) -> HubSpotApiResult:
		"""
		Creates a new contact or updates an existing one based on email.
		"""
		if not self.client:
			logfire.error("HubSpot client not initialized. Cannot manage contact.")
			return HubSpotApiResult(status="error", entity_type="contact", message="HubSpot client not initialized.")
		
		if not contact_input.properties.email:
			logfire.warning("Cannot create or update contact without an email address.")
			return HubSpotApiResult(status="error", entity_type="contact", message="Email is required to create or update contact.")
		
		# Prepare properties for HubSpot API (convert Pydantic model to dict)
		properties_dict = contact_input.properties.model_dump(exclude_none=True, by_alias=True)
		hubspot_input = SimplePublicObjectInput(properties=properties_dict)
		
		try:
			# 1. Check if contact exists by email
			existing_contact_id = self.search_contact_by_email(contact_input.properties.email)
			
			if existing_contact_id:
				# 2. Update existing contact
				logfire.info(f"Updating existing HubSpot contact ID: {existing_contact_id}")
				updated_contact = self.client.crm.contacts.basic_api.update(
					contact_id=existing_contact_id,
					simple_public_object_input=hubspot_input
				)
				logfire.info(f"Successfully updated contact ID: {updated_contact.id}")
				return HubSpotApiResult(
					status="updated",
					entity_type="contact",
					hubspot_id=updated_contact.id,
					message=f"Contact updated successfully.",
					details=updated_contact.to_dict() # Return HubSpot response data if needed
				)
			else:
				# 3. Create new contact
				logfire.info(f"Creating new HubSpot contact for email: {contact_input.properties.email}")
				created_contact = self.client.crm.contacts.basic_api.create(
					simple_public_object_input=hubspot_input
				)
				logfire.info(f"Successfully created contact ID: {created_contact.id}")
				return HubSpotApiResult(
					status="created",
					entity_type="contact",
					hubspot_id=created_contact.id,
					message=f"Contact created successfully.",
					details=created_contact.to_dict()
				)
		
		except ContactsApiException as e:
			return self._handle_api_exception(e, "create/update", "contact", entity_data=properties_dict)
		except Exception as e: # Catch other potential errors
			return self._handle_api_exception(e, "create/update", "contact", entity_data=properties_dict)
	
	
	def create_deal(self, deal_input: HubSpotDealInput) -> HubSpotApiResult:
		"""
		Creates a new deal in HubSpot.
		Optionally associates it with other objects (e.g., contacts).
		Note: Updating deals often requires knowing the deal ID. This example focuses on creation.
		"""
		if not self.client:
			logfire.error("HubSpot client not initialized. Cannot create deal.")
			return HubSpotApiResult(status="error", entity_type="deal", message="HubSpot client not initialized.")
		
		if not deal_input.properties.dealname:
			logfire.warning("Cannot create deal without a deal name.")
			return HubSpotApiResult(status="error", entity_type="deal", message="Deal name is required.")
		
		# Prepare properties and associations for HubSpot API
		properties_dict = deal_input.properties.model_dump(exclude_none=True, by_alias=True)
		# associations = deal_input.associations # Add logic to handle associations if needed
		
		hubspot_input = DealSimplePublicObjectInput(
			properties=properties_dict,
			# associations=associations # Pass associations here if using them
		)
		
		try:
			logfire.info(f"Creating new HubSpot deal: {deal_input.properties.dealname}")
			created_deal = self.client.crm.deals.basic_api.create(
				simple_public_object_input=hubspot_input
			)
			logfire.info(f"Successfully created deal ID: {created_deal.id}")
			return HubSpotApiResult(
				status="created",
				entity_type="deal",
				hubspot_id=created_deal.id,
				message=f"Deal '{created_deal.properties.get('dealname')}' created successfully.",
				details=created_deal.to_dict()
			)
		
		except DealsApiException as e:
			return self._handle_api_exception(e, "create", "deal", entity_data=properties_dict)
		except Exception as e: # Catch other potential errors
			return self._handle_api_exception(e, "create", "deal", entity_data=properties_dict)
	
	# --- Add methods for other HubSpot operations as needed ---
	# e.g., update_deal, get_deal, create_custom_object, associate_objects, etc.
	
	# Example: Associate Deal with Contact
	def associate_deal_with_contact(self, deal_id: str, contact_id: str) -> bool:
		"""Associates an existing deal with an existing contact."""
		if not self.client: return False
		try:
			# Association type ID 3 = Deal to Contact
			association_type_id = 3
			self.client.crm.deals.associations_api.create(
				deal_id=deal_id,
				to_object_type="contacts", # Use plural object type name here
				to_object_id=contact_id,
				association_type=str(association_type_id)
			)
			logfire.info(f"Successfully associated deal {deal_id} with contact {contact_id}")
			return True
		except DealsApiException as e:
			self._handle_api_exception(e, "associate deal->contact", "association", entity_data={"deal": deal_id, "contact": contact_id})
			return False
		except Exception as e:
			self._handle_api_exception(e, "associate deal->contact", "association", entity_data={"deal": deal_id, "contact": contact_id})
			return False

"""
**Instructions:**
1.  Create a file named `hubspot_service.py` inside the `app/services/` directory.
2.  Paste this code into it.
3.  This class provides basic create/update functionality. You'll likely need to expand it with more methods (updating deals, handling custom objects, more complex associations) based on the project's full requirements.
4.  Error handling is basic; you might need more sophisticated retry logic or specific error mapping depending on HubSpot API behavi
"""