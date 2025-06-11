"""Configuration loading utilities for Bland AI."""

import os
import json
import logfire
from typing import Dict, Any
from app.core.config import settings

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(_SCRIPT_DIR))))
PATHWAY_JSON_PATH = os.path.join(_PROJECT_ROOT, "app", "assets", "call.json")
LOCATION_TOOL_JSON_PATH = os.path.join(
    _PROJECT_ROOT, "app", "assets", "location.json")
QUOTE_TOOL_JSON_PATH = os.path.join(
    _PROJECT_ROOT, "app", "assets", "quote.json")


def load_pathway_definition() -> Dict[str, Any]:
  """
  Loads the pathway definition from the JSON file.
  Also loads knowledge base content from knowledge.json and injects it into Knowledge Base nodes.
  Replaces development webhook URLs with production URLs and removes hardcoded API keys.
  """
  try:
    with open(PATHWAY_JSON_PATH, "r") as f:
      pathway_data = json.load(f)
      logfire.info(
          f"Successfully loaded pathway definition from {PATHWAY_JSON_PATH}"
      )

      # Load knowledge base content from knowledge.json
      knowledge_json_path = os.path.join(
          _PROJECT_ROOT, "app", "assets", "knowledge.json")
      try:
        with open(knowledge_json_path, "r") as kb_file:
          knowledge_data = json.load(kb_file)
          knowledge_text = knowledge_data.get("text", "")

          # Inject knowledge base content into Knowledge Base nodes
          if "nodes" in pathway_data:
            for node in pathway_data["nodes"]:
              if node.get("type") == "Knowledge Base" and "data" in node:
                node["data"]["knowledgeBase"] = knowledge_text
                logfire.info(
                    f"Injected knowledge base content into node {node.get('id')}")

              # Replace development webhook URLs with production URLs and remove hardcoded API keys
              if node.get("type") == "Webhook" and "data" in node:
                # Replace ngrok URLs with production URLs
                if "url" in node["data"] and "ngrok-free.app" in node["data"]["url"]:
                  old_url = node["data"]["url"]
                  # Extract the endpoint path from the ngrok URL
                  path = old_url.split(
                      "/api/")[1] if "/api/" in old_url else ""
                  # Use the base URL from settings with the extracted path
                  base_url = settings.BASE_URL.rstrip("/")  # type: ignore
                  new_url = f"{base_url}/api/{path}"
                  node["data"]["url"] = new_url
                  logfire.info(
                      f"Replaced webhook URL in node {node.get('id')}: {old_url} -> {new_url}")

                # Replace hardcoded API keys with configuration values
                if "headers" in node["data"] and "Authorization" in node["data"]["headers"]:
                  # Use the API key from settings
                  new_auth = f"Bearer {settings.PRICING_WEBHOOK_API_KEY}"
                  node["data"]["headers"]["Authorization"] = new_auth
                  logfire.info(
                      f"Replaced hardcoded API key in node {node.get('id')}")

        logfire.info(
            f"Successfully loaded and injected knowledge base from {knowledge_json_path}")
      except Exception as kb_e:
        logfire.error(
            f"Error loading knowledge base from {knowledge_json_path}: {kb_e}",
            exc_info=True,
        )
        # Continue with the original pathway data even if knowledge base loading fails

      return pathway_data
  except FileNotFoundError:
    logfire.error(
        f"Pathway definition file not found at {PATHWAY_JSON_PATH}. Cannot sync pathway."
    )
    return {}
  except json.JSONDecodeError as e:
    logfire.error(
        f"Error decoding JSON from {PATHWAY_JSON_PATH}: {e}", exc_info=True
    )
    return {}
  except Exception as e:
    logfire.error(
        f"Error loading pathway definition from {PATHWAY_JSON_PATH}: {e}",
        exc_info=True,
    )
    return {}


def load_location_tool_definition() -> Dict[str, Any]:
  """Loads the location tool definition from the JSON file."""
  try:
    with open(LOCATION_TOOL_JSON_PATH, "r") as f:
      location_data = json.load(f)
      logfire.info(
          f"Successfully loaded location tool definition from {LOCATION_TOOL_JSON_PATH}"
      )
      return location_data
  except FileNotFoundError:
    logfire.error(
        f"Location tool definition file not found at {LOCATION_TOOL_JSON_PATH}. Cannot load location tool."
    )
    return {}
  except json.JSONDecodeError as e:
    logfire.error(
        f"Error decoding JSON from {LOCATION_TOOL_JSON_PATH}: {e}", exc_info=True
    )
    return {}
  except Exception as e:
    logfire.error(
        f"Error loading location tool definition from {LOCATION_TOOL_JSON_PATH}: {e}",
        exc_info=True,
    )
    return {}


def load_quote_tool_definition() -> Dict[str, Any]:
  """Loads the quote tool definition from the JSON file."""
  try:
    with open(QUOTE_TOOL_JSON_PATH, "r") as f:
      quote_data = json.load(f)
      logfire.info(
          f"Successfully loaded quote tool definition from {QUOTE_TOOL_JSON_PATH}"
      )
      return quote_data
  except FileNotFoundError:
    logfire.error(
        f"Quote tool definition file not found at {QUOTE_TOOL_JSON_PATH}. Cannot load quote tool."
    )
    return {}
  except json.JSONDecodeError as e:
    logfire.error(
        f"Error decoding JSON from {QUOTE_TOOL_JSON_PATH}: {e}", exc_info=True
    )
    return {}
  except Exception as e:
    logfire.error(
        f"Error loading quote tool definition from {QUOTE_TOOL_JSON_PATH}: {e}",
        exc_info=True,
    )
    return {}


def prepare_tool_json_data(tool_definition: Dict[str, Any]) -> Dict[str, Any]:
  """
  Prepares the JSON data for a tool update.
  Returns a dictionary with the tool configuration.
  """
  return {
      "name": tool_definition.get("name"),
      "description": tool_definition.get("description"),
      "url": tool_definition.get("url"),
      "headers": tool_definition.get("headers", {}),
      "input_schema": tool_definition.get("input_schema", {}),
      "type": tool_definition.get("type", "object"),
      "method": tool_definition.get("method", "POST"),
      "required": tool_definition.get("required", []),
      "body": tool_definition.get("body", {}),
      "response": tool_definition.get("response", {}),
      "speech": tool_definition.get("speech", None),
      "timeout": tool_definition.get("timeout", 10000),
  }
