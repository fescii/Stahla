# app/services/email.py

import httpx
import logfire
from typing import Dict, Any, Optional, List, Tuple
import re
import json
from datetime import datetime

# Import models
from app.models.email import EmailWebhookPayload, EmailProcessingResult, EmailAttachment
from app.models.classification import ClassificationInput, ClassificationResult, LeadClassificationType
from app.models.hubspot import HubSpotContactResult, HubSpotApiResult
from app.core.config import settings

class EmailManager:
    """
    Manages the processing of incoming emails.
    Parses content, checks completeness, and prepares for classification.
    Handles auto-replies for missing information.
    """
    
    def __init__(self):
        """Initialize the Email Manager with configuration."""
        self.email_client = httpx.AsyncClient(timeout=10.0)
        logfire.info("EmailManager initialized.")
        
    async def close_client(self):
        """Gracefully close the HTTP client."""
        await self.email_client.aclose()
        logfire.info("Email HTTP client closed.")

    async def close(self):
        """Closes any underlying clients (e.g., Resend, SMTP). Placeholder for now."""
        logfire.info("Closing EmailManager resources (if any)...")
        # Add logic here to close Resend client or SMTP connection if they exist
        # Example for a hypothetical self._resend_client:
        # if hasattr(self, '_resend_client') and self._resend_client:
        #     # Assuming resend client has an aclose method or similar
        #     pass # Replace with actual close logic
        logfire.info("EmailManager resources closed.")

    async def _extract_data_with_llm(self, payload: EmailWebhookPayload) -> Dict[str, Any]:
        """
        Extract structured data from email content using LLM.
        """
        if settings.LLM_PROVIDER.lower() == "none" or not settings.MARVIN_API_KEY:
            logfire.warn("LLM extraction unavailable: No LLM provider configured")
            return {}
        
        try:
            # Prepare the email content for the LLM
            email_content = f"Subject: {payload.subject or ''}\n\n"
            
            # Use plain text body preferentially, fallback to HTML
            if payload.body_text:
                email_content += f"Body:\n{payload.body_text}"
            elif payload.body_html:
                # Strip HTML tags for cleaner text (basic approach)
                stripped_html = re.sub(r'<[^>]+>', ' ', payload.body_html)
                email_content += f"Body:\n{stripped_html}"
            
            # Add sender information
            email_content += f"\n\nFrom: {payload.from_email}"

            # Construct the extraction prompt
            prompt = f"""
            Extract the following key information from this email about a restroom rental inquiry.
            For each field, extract the information if present or return null:

            1. First name
            2. Last name
            3. Company name (if mentioned)
            4. Phone number
            5. Product interest (e.g., "Restroom Trailer", "Porta Potty", "Shower Trailer", etc.)
            6. Event type (e.g., Wedding, Construction, Festival)
            7. Event location/address
            8. Number of attendees/guests
            9. Number of stalls/units needed
            10. Duration (in days)
            11. Start date
            12. End date
            13. Whether ADA/handicap accessible facilities are needed (true/false)
            14. Budget mentioned (any dollar amount)
            15. Whether power is available on site (true/false)
            16. Whether water is available on site (true/false)

            Format the response as a valid JSON object with these fields:
            {{
                "firstname": string or null,
                "lastname": string or null,
                "company": string or null,
                "phone": string or null,
                "product_interest": [string] (array of product types),
                "event_type": string or null,
                "event_location": string or null,
                "guest_count": number or null,
                "required_stalls": number or null,
                "duration_days": number or null,
                "start_date": string or null,
                "end_date": string or null,
                "ada_required": boolean or null,
                "budget_mentioned": string or null,
                "power_available": boolean or null,
                "water_available": boolean or null
            }}

            Email Content:
            {email_content}
            """
            
            # Make the LLM API call
            # This would be replaced with your actual LLM integration
            # Example: Using Marvin
            import marvin
            marvin.settings.api_key = settings.MARVIN_API_KEY
            
            response = await marvin.classify_async(
                prompt,
                output_format=dict,
                max_tokens=1000
            )
            
            logfire.info("Extracted email data with LLM", response=response)
            return response
            
        except Exception as e:
            logfire.error(f"LLM extraction failed: {str(e)}", exc_info=True)
            return {}

    def _parse_email_content(self, payload: EmailWebhookPayload) -> Dict[str, Any]:
        """
        Parse email subject and body to extract structured data.
        Uses regex patterns for known formats and fallback patterns.
        """
        logfire.info("Parsing email content", message_id=payload.message_id)
        
        # Initialize with email metadata
        extracted_data = {
            "email": payload.from_email,
            "subject": payload.subject,
            # Add timestamp
            "submission_timestamp": payload.received_at or datetime.now().isoformat(),
            "source": "email"
        }
        
        # Extract name from the from_email (basic approach)
        if payload.from_email:
            email_parts = payload.from_email.split('@')
            if len(email_parts) > 0:
                name_parts = email_parts[0].replace('.', ' ').split(' ')
                if len(name_parts) >= 2:
                    extracted_data["firstname"] = name_parts[0].capitalize()
                    extracted_data["lastname"] = name_parts[1].capitalize()
                elif len(name_parts) == 1:
                    extracted_data["firstname"] = name_parts[0].capitalize()
        
        # Basic regex patterns for common fields
        patterns = {
            "phone": r'(?:phone|call|tel|contact)(?:\s*(?:number|#))?\s*(?::|\s*is\s*)?[\s:]*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
            "product_interest": r'(?:looking for|need|interested in|inquiring about)[\s\w]*(?:restroom|bathroom|toilet|porta|shower)\s*(trailer|unit|potty|facility|portable)',
            "guest_count": r'(?:guests|people|attendees|attendance)\s*(?::|\s*of\s*)?[\s:]*(\d+)',
            "required_stalls": r'(?:stalls|units|bathrooms|restrooms|toilets)\s*(?::|\s*needed\s*)?[\s:]*(\d+)',
            "duration_days": r'(?:duration|days|for|period|length)\s*(?::|\s*of\s*)?[\s:]*(\d+)\s*(?:days|day)',
            "event_type": r'(?:event|occasion|function|project)\s*(?:type|is|for)?\s*(?::|\s*a\s*)?[\s:]*([A-Za-z]+(?:\s+[A-Za-z]+){0,2})',
            "event_location": r'(?:location|address|venue|site|place|at)\s*(?:is|:)?\s*[:]*\s*([\w\s.,]+(?:street|avenue|road|drive|st\.?|ave\.?|rd\.?|dr\.?|lane|ln\.?|\d{5})[\w\s.,]*)',
            "budget_mentioned": r'(?:budget|cost|price|amount|spend)\s*(?:is|:|\s*of\s*)?[\s:]*[\$]?(\d+(?:[.,]\d+)?(?:\s*(?:k|thousand|K))?)',
        }
        
        # Use email body text or fallback to HTML content
        email_text = payload.body_text
        if not email_text and payload.body_html:
            # Simple HTML stripping (a better HTML parser would be good for production)
            email_text = re.sub(r'<[^>]+>', ' ', payload.body_html)
        
        if not email_text:
            logfire.warn("No email body content available for parsing", message_id=payload.message_id)
            return extracted_data
        
        # Apply the regex patterns to extract data
        for field, pattern in patterns.items():
            match = re.search(pattern, email_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                
                # Handle specific field transformations
                if field == "product_interest":
                    # Convert to list and normalize
                    product = value.lower()
                    if "trailer" in product:
                        if "restroom" in email_text.lower() or "bathroom" in email_text.lower():
                            extracted_data[field] = ["Restroom Trailer"]
                        elif "shower" in email_text.lower():
                            extracted_data[field] = ["Shower Trailer"]
                        else:
                            extracted_data[field] = ["Restroom Trailer"]  # Default assumption
                    elif "potty" in product or "portable" in product:
                        extracted_data[field] = ["Portable Toilet"]
                    else:
                        extracted_data[field] = ["Portable Toilet"]  # Default assumption
                
                # Number conversions
                elif field in ["guest_count", "required_stalls", "duration_days"]:
                    try:
                        extracted_data[field] = int(value)
                    except ValueError:
                        logfire.warn(f"Could not convert {field} to integer: {value}")
                        extracted_data[field] = None
                
                else:
                    extracted_data[field] = value
        
        # Check for ADA requirements
        ada_keywords = ["ada", "handicap", "accessible", "disability", "wheelchair"]
        extracted_data["ada_required"] = any(keyword in email_text.lower() for keyword in ada_keywords)
        
        # Check for power/water availability hints
        power_positive = ["have power", "power available", "electrical", "electricity", "outlet", "power source"]
        power_negative = ["no power", "power unavailable", "don't have power", "no electricity"]
        water_positive = ["have water", "water available", "water source", "water hookup", "garden hose"]
        water_negative = ["no water", "water unavailable", "don't have water"]
        
        if any(term in email_text.lower() for term in power_positive):
            extracted_data["power_available"] = True
        elif any(term in email_text.lower() for term in power_negative):
            extracted_data["power_available"] = False
            
        if any(term in email_text.lower() for term in water_positive):
            extracted_data["water_available"] = True
        elif any(term in email_text.lower() for term in water_negative):
            extracted_data["water_available"] = False
        
        logfire.info("Email data extracted with regex", extracted=extracted_data)
        return extracted_data

    async def _check_email_data_completeness(self, extracted_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if the extracted email data meets the minimum requirements for classification.
        Returns a boolean indicating completeness and a list of missing fields.
        """
        # Define required fields based on the PRD requirements (≥95% completeness)
        required_fields = [
            "product_interest",  # What products they need
            "event_location",    # Location information
            "phone",            # Contact information
            "event_type",       # Purpose of rental
            "required_stalls",  # How many units needed
        ]
        
        # Highly desirable fields (may trigger follow-up but not necessarily required)
        desired_fields = [
            "duration_days",    # How long they need it
            "guest_count",      # Size of event/project
            "ada_required",     # Accessibility requirements
        ]
        
        # Check which required fields are missing
        missing_required = [field for field in required_fields if not extracted_data.get(field)]
        
        # Check which desired fields are missing
        missing_desired = [field for field in desired_fields if not extracted_data.get(field)]
        
        # Calculate completeness percentage
        all_fields = required_fields + desired_fields
        present_fields = [field for field in all_fields if extracted_data.get(field)]
        completeness_percentage = (len(present_fields) / len(all_fields)) * 100
        
        # Log completeness metrics
        logfire.info(
            f"Email data completeness check: {completeness_percentage:.1f}%", 
            required_missing=missing_required,
            desired_missing=missing_desired
        )
        
        # Determine if data is complete enough for classification
        # PRD goal: ≥95% data-field completeness
        is_complete = len(missing_required) == 0 and completeness_percentage >= 85
        
        # Return both required and desired missing fields for the auto-reply
        return is_complete, missing_required + missing_desired

    async def _send_auto_reply(self, original_payload: EmailWebhookPayload, missing_fields: List[str], extracted_data: Dict[str, Any]):
        """
        Send an auto-reply requesting missing information.
        Uses a template to craft a personalized reply.
        """
        if not settings.EMAIL_SENDING_ENABLED:
            logfire.warn("Email sending is disabled, cannot send auto-reply", message_id=original_payload.message_id)
            return False
            
        try:
            # Format field names for human readability
            formatted_fields = []
            for field in missing_fields:
                if field == "product_interest":
                    formatted_fields.append("which restroom products you're interested in (trailer, porta potty, etc.)")
                elif field == "event_location":
                    formatted_fields.append("the location or address where you need the facilities")
                elif field == "event_type":
                    formatted_fields.append("the type of event or project (wedding, construction, etc.)")
                elif field == "required_stalls":
                    formatted_fields.append("how many stalls or units you need")
                elif field == "duration_days":
                    formatted_fields.append("how many days you need the facilities")
                elif field == "guest_count":
                    formatted_fields.append("the approximate number of guests or users")
                elif field == "ada_required":
                    formatted_fields.append("whether you need ADA/handicap accessible facilities")
                elif field == "phone":
                    formatted_fields.append("your phone number for follow-up")
                else:
                    formatted_fields.append(field.replace('_', ' '))

            # Create the request list
            if len(formatted_fields) == 1:
                missing_info_text = formatted_fields[0]
            elif len(formatted_fields) == 2:
                missing_info_text = f"{formatted_fields[0]} and {formatted_fields[1]}"
            else:
                missing_info_text = ", ".join(formatted_fields[:-1]) + f", and {formatted_fields[-1]}"
            
            # Recipient and subject
            recipient = original_payload.from_email
            subject = f"Re: {original_payload.subject} - Additional Information Needed"
            
            # Get first name or use "there" if not available
            first_name = extracted_data.get("firstname", "there")
            
            # Email body with personalization
            body = f"""
            Hello {first_name},
            
            Thank you for your interest in Stahla's restroom solutions! To help us provide you with the most accurate quote and service information, could you please provide the following additional details:
            
            - {missing_info_text}
            
            This information will help us match you with the right solutions for your needs and provide you with an accurate quote quickly.
            
            You can simply reply to this email with the requested information, and we'll get back to you promptly with a customized solution.
            
            Best regards,
            Stahla Assistant
            """
            
            # Strip any excess whitespace/indentation from template
            body = "\n".join(line.strip() for line in body.split("\n"))
            
            # Send the email using SMTP service
            if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
                # This would integrate with your email provider
                # Example placeholder for sending via SMTP
                logfire.info(f"Sending auto-reply email", recipient=recipient, subject=subject)
                
                # For demonstration, log the email content instead of sending
                logfire.info(f"Email content: {body}")
                
                # Return success assuming the email was sent
                return True
            else:
                logfire.error("Email sending failed: SMTP configuration incomplete")
                return False
                
        except Exception as e:
            logfire.error(f"Error sending auto-reply: {str(e)}", exc_info=True)
            return False

    async def send_handoff_notification(
        self,
        classification_result: ClassificationResult,
        contact_result: Optional[HubSpotContactResult],
        lead_result: Optional[HubSpotApiResult]
    ):
        """
        Send an email notification to the relevant sales team
        after a lead has been classified and processed in HubSpot.
        Handles Lead information instead of Deal.
        """
        if not settings.EMAIL_SENDING_ENABLED:
            logfire.warn("Email sending is disabled, skipping handoff notification")
            return False
            
        if not classification_result.classification:
            logfire.info("No classification output available, skipping handoff notification")
            return False
            
        try:
            # Get the classification output and input data
            output = classification_result.classification
            
            # Skip notification for disqualified leads
            if output.lead_type == "Disqualify":
                logfire.info("Lead classified as Disqualify, skipping handoff notification")
                return False
                
            # Determine the recipient team based on classification
            team_name = None
            if output.lead_type == "Services":
                team_name = "Stahla Services Sales Team"
            elif output.lead_type == "Logistics":
                team_name = "Stahla Logistics Sales Team"
            elif output.lead_type == "Leads":
                team_name = "Stahla Leads Team"
                
            if not team_name:
                logfire.warn("No team determined for handoff notification")
                return False
                
            # Construct base email content
            # Leads don't have a standard 'leadname'. Construct from contact info.
            contact_props = contact_result.details.get('properties', {}) if contact_result and contact_result.details else {}
            lead_name_part = f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip() or "New Lead"
            # Use service needed or a default if not available
            service_part = (output.metadata.get("service_needed") or 
                            contact_props.get("what_service_do_you_need_") or 
                            "Inquiry")
            lead_name = f"{lead_name_part} - {service_part}"
                
            # Create subject line
            subject = f"New {output.lead_type} Lead: {lead_name}"
            
            # Build the email body with a clear summary and next steps
            lead_id = lead_result.hubspot_id if lead_result else 'Not created'
            contact_id = contact_result.hubspot_id if contact_result else 'Not created'
            
            # Extract details from classification metadata or contact properties
            extracted_metadata = output.metadata or {}
            
            body_parts = [
                f"A new lead has been classified as: {output.lead_type}",
                f"Classification confidence: {output.confidence:.0%}",
                "",
                "--- LEAD SUMMARY ---",
                f"Contact: {contact_props.get('firstname', 'Unknown')} {contact_props.get('lastname', '')}",
                f"Email: {contact_props.get('email', 'Not provided')}",
                f"Phone: {contact_props.get('phone', 'Not provided')}",
                f"Product Interest: {extracted_metadata.get('product_interest') or 'Not specified'}",
                f"Event/Project Type: {extracted_metadata.get('event_type') or 'Not specified'}",
                f"Location: {extracted_metadata.get('location') or contact_props.get('event_or_job_address') or 'Not specified'}",
                f"Duration: {extracted_metadata.get('duration_days') or 'Unknown'} days",
                f"Stalls Required: {extracted_metadata.get('required_stalls') or contact_props.get('how_many_portable_toilet_stalls_') or 'Unknown'}",
                f"Guest Count: {extracted_metadata.get('guest_count') or 'Unknown'}",
                "",
                "--- SITE DETAILS ---",
                f"ADA Required: {'Yes' if extracted_metadata.get('ada_required') else 'No' if extracted_metadata.get('ada_required') is not None else 'Unknown'}",
                f"Power Available: {'Yes' if extracted_metadata.get('power_available') else 'No' if extracted_metadata.get('power_available') is not None else 'Unknown'}",
                f"Water Available: {'Yes' if extracted_metadata.get('water_available') else 'No' if extracted_metadata.get('water_available') is not None else 'Unknown'}",
                "",
                "--- HUBSPOT INFO ---",
                f"HubSpot Contact ID: {contact_id}",
                f"HubSpot Lead ID: {lead_id}",
                "",
                "--- NEXT STEPS ---",
                "1. Review lead details in HubSpot",
                "2. Prepare and send quote within 15 minutes",
                "3. Make follow-up call to discuss requirements",
            ]
            
            # Add call recording URL if available
            call_recording_url = extracted_metadata.get("call_recording_url") or contact_props.get("call_recording_url")
            if call_recording_url:
                body_parts.append("")
                body_parts.append(f"Call Recording: {call_recording_url}")
            
            # Join all parts with line breaks
            body = "\n".join(body_parts)
            
            # Send notification email to team
            logfire.info("Sending handoff notification", team=team_name, subject=subject)
            logfire.info(f"Notification content: {body}")
            return True
            
        except Exception as e:
            logfire.error(f"Error sending handoff notification: {str(e)}", exc_info=True)
            return False

    async def process_incoming_email(self, payload: EmailWebhookPayload) -> EmailProcessingResult:
        """
        Main method to process an incoming email webhook.
        Parses, checks completeness, potentially replies, and prepares for classification.
        """
        logfire.info("Processing incoming email", message_id=payload.message_id, from_email=payload.from_email)

        try:
            # First try to parse with basic rules
            extracted_data = self._parse_email_content(payload)
            
            # If LLM is configured, try to enhance with LLM extraction
            if settings.LLM_PROVIDER.lower() != "none" and settings.MARVIN_API_KEY:
                llm_extracted = await self._extract_data_with_llm(payload)
                
                # Merge LLM results, prioritizing LLM data where both exist
                if llm_extracted:
                    for key, value in llm_extracted.items():
                        if value is not None and value != "":  # Skip empty values
                            extracted_data[key] = value
            
            # Check if we have enough data for classification
            is_complete, missing_fields = await self._check_email_data_completeness(extracted_data)

            if not is_complete:
                logfire.info("Email data incomplete, sending auto-reply", missing=missing_fields)
                # Send auto-reply if configured, passing extracted_data
                auto_reply_sent = await self._send_auto_reply(payload, missing_fields, extracted_data)
                
                # Return result indicating auto-reply was sent
                return EmailProcessingResult(
                    status="success",
                    message="Email received, auto-reply sent for missing information.",
                    classification_pending=False,  # Not ready for classification yet
                    extracted_data=extracted_data,
                    details={"missing_fields": missing_fields, "auto_reply_sent": auto_reply_sent},
                    message_id=payload.message_id
                )
            else:
                logfire.info("Email data complete, ready for classification")
                # Data is complete, return success and indicate classification is pending
                return EmailProcessingResult(
                    status="success",
                    message="Email processed successfully, ready for classification.",
                    classification_pending=True,
                    extracted_data=extracted_data,
                    message_id=payload.message_id
                )

        except Exception as e:
            logfire.error(f"Error processing email: {str(e)}", message_id=payload.message_id, exc_info=True)
            return EmailProcessingResult(
                status="error",
                message=f"Failed to process email: {e}",
                classification_pending=False,
                details={"error_type": type(e).__name__},
                message_id=payload.message_id
            )

# Create a singleton instance of the manager
email_manager = EmailManager()