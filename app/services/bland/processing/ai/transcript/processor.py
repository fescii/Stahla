"""
Transcript processing service for Bland voice webhooks.

Handles extraction and cleaning of transcript data from various webhook payload formats.
"""

from typing import Optional
from app.models.bland import BlandWebhookPayload


class TranscriptProcessor:
  """
  Processes and extracts transcript data from Bland webhook payloads.

  Handles multiple transcript formats:
  - Concatenated transcript (preferred)
  - Summary text
  - Individual transcript entries
  """

  def extract_transcript(self, webhook_payload: BlandWebhookPayload) -> Optional[str]:
    """
    Extract transcript text from webhook payload.

    Args:
        webhook_payload: Bland webhook payload

    Returns:
        Extracted transcript text or None if not available
    """
    # Try concatenated transcript first (most complete)
    if webhook_payload.concatenated_transcript:
      return webhook_payload.concatenated_transcript.strip()

    # Try summary if available
    if webhook_payload.summary:
      return webhook_payload.summary.strip()

    # Build from individual transcript entries
    if webhook_payload.transcripts:
      transcript_parts = []
      for entry in webhook_payload.transcripts:
        if entry.text and entry.text.strip():
          speaker = entry.user or "Speaker"
          transcript_parts.append(f"{speaker}: {entry.text.strip()}")

      if transcript_parts:
        return "\n".join(transcript_parts)

    return None

  def extract_variables_data(self, webhook_payload: BlandWebhookPayload) -> dict:
    """
    Extract structured data from webhook variables.

    Args:
        webhook_payload: Bland webhook payload

    Returns:
        Dictionary containing cleaned variables data
    """
    variables_data = {}

    # Extract from main variables
    if webhook_payload.variables:
      variables_data.update(webhook_payload.variables)

    # Extract from metadata
    if webhook_payload.metadata:
      variables_data.update(webhook_payload.metadata)

    # Clean and normalize the data
    cleaned_data = {}
    for key, value in variables_data.items():
      if value is not None and value != "None" and str(value).strip():
        cleaned_data[key] = value

    return cleaned_data

  def get_transcript_summary(self, transcript: str, max_length: int = 500) -> str:
    """
    Create a summary of the transcript for processing.

    Args:
        transcript: Full transcript text
        max_length: Maximum length for summary

    Returns:
        Summarized transcript text
    """
    if not transcript:
      return ""

    if len(transcript) <= max_length:
      return transcript

    return transcript[:max_length] + "..."


# Global instance
transcript_processor = TranscriptProcessor()
