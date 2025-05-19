<!-- filepath: /docs/marvin.md -->

# Marvin AI Integration for Lead Classification

This document details how the Marvin AI library is utilized within the Stahla AI SDR application, specifically for lead classification based on call summaries or transcripts. The integration is primarily managed through `app/services/classify/marvin.py` and used by `app/services/classify/classification.py`.

## 1. Configuration

Marvin's setup is handled by the `configure_marvin()` function in `app/services/classify/marvin.py`.

- **Provider Selection:** The choice of LLM provider is determined by the `LLM_PROVIDER` setting in `app.core.config.settings`. Supported providers that are explicitly configured include "openai", "anthropic", "gemini", and "marvin" itself.
- **API Keys & Model:**
  - Based on the `LLM_PROVIDER`, the function expects corresponding API key(s) (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) and optionally a model name (e.g., `MODEL_NAME`) from the application settings.
  - These settings are used to configure `marvin.settings` attributes dynamically (e.g., `marvin.settings.openai_api_key`, `marvin.settings.openai_model_name`).
  - If `LLM_PROVIDER` is set to "marvin", the system assumes that `MARVIN_API_KEY` (if set in the environment or application settings) will be automatically picked up by the Marvin library.
- **Initialization:** This configuration step is typically performed when the application starts or when the Marvin-related services are first initialized, ensuring Marvin is ready before being called for classification tasks.

## 2. Core AI Classification Function: `classify_lead_with_ai`

Defined in `app/services/classify/marvin.py`, this is the central Marvin-powered function for analyzing call data.

- **Decorator:** `@marvin.fn` - This decorator transforms the Python function into an AI function that Marvin can execute using an LLM.
- **Input:**
  - `call_summary_or_transcript: str`: A string containing either a summary of the call or the full call transcript.
- **Output:**
  - `ExtractedCallDetails` (Pydantic Model): This model serves as the structured output format that Marvin is instructed to populate. It includes:
    - `classification: LeadClassificationType`: The final classification category (Services, Logistics, Leads, or Disqualify).
    - `reasoning: str`: A textual explanation for the assigned classification.
    - A comprehensive set of other fields that Marvin attempts to extract from the input text, such as:
      - `product_interest: Optional[List[ProductType]]`
      - `service_needed: Optional[str]`
      - `event_type: Optional[str]`
      - `location: Optional[str]` (full address)
      - `city: Optional[str]`
      - `state: Optional[str]` (2-letter code)
      - `postal_code: Optional[str]`
      - `start_date: Optional[str]` (YYYY-MM-DD)
      - `end_date: Optional[str]` (YYYY-MM-DD)
      - `duration_days: Optional[int]`
      - `guest_count: Optional[int]`
      - `required_stalls: Optional[int]`
      - `ada_required: Optional[bool]`
      - `power_available: Optional[bool]`
      - `water_available: Optional[bool]`
      - `budget_mentioned: Optional[str]`
      - `comments: Optional[str]`
- **Operational Logic (Guided by Docstring):**
  The power of this Marvin function lies in its detailed docstring, which provides natural language instructions to the LLM.
  - **Classification Rules:** The docstring explicitly lists various scenarios based on combinations of "Intended Use," "Product Type," "Stalls," "Duration," and "Location" (local vs. non-local, determined by a 3-hour drive time from key service hubs). These rules guide the LLM in assigning the lead to "Services," "Logistics," "Leads," or "Disqualify."
    - _Example Rule (Small Event / Trailer / Local):_
      - Intended Use = Small Event
      - Product Type = Any "specialty trailer"
      - Stalls < 8
      - Duration > 5 days
      - Location: ≤ 3 hours drive time
      - -> Results in "Services" classification.
  - **Extraction Guidelines:** The docstring instructs Marvin to extract specific pieces of information (as listed in the `ExtractedCallDetails` output model). A crucial instruction is that all extracted date strings **must be formatted as 'YYYY-MM-DD'**.
  - **Disqualification Criteria:** Clear conditions are provided for when a lead should be marked as "Disqualify" (e.g., incorrect information, service not offered, scam/spam, explicit non-interest).

## 3. `MarvinClassificationManager`

This class in `app/services/classify/marvin.py` acts as a wrapper and utility layer around the `classify_lead_with_ai` Marvin function.

- **`get_lead_classification(self, input_data: ClassificationInput) -> ClassificationOutput`:**
  - This is the main method invoked by the higher-level `ClassificationManager`.
  - It first attempts to find the call text (summary or transcript) from the `input_data` (looking in `extracted_data` and `raw_data`).
  - If call text is found, it calls `classify_lead_with_ai(call_text)`.
  - The `ExtractedCallDetails` object returned by Marvin is then used to construct a `ClassificationOutput` object.
    - The `lead_type` and `reasoning` are taken directly from Marvin's output.
    - The entire `ExtractedCallDetails` object (containing all extracted fields) is converted to a dictionary using `model_dump(exclude_none=True)` and stored in the `metadata` field of the `ClassificationOutput`.
  - It also determines an `assigned_owner_team` based on the classification provided by Marvin.
  - If no call text is available in the input, it defaults to classifying the lead as "Leads" with an appropriate error message as reasoning and sets `requires_human_review` to true.

## 4. Integration into the Main Classification Workflow

The `ClassificationManager` in `app/services/classify/classification.py` integrates Marvin as follows:

- **`classify_lead_data(self, input_data: ClassificationInput) -> ClassificationResult`:**
  1.  **Conditional Invocation:** It checks if Marvin-based classification is enabled by verifying `settings.LLM_PROVIDER == "marvin"` and the presence of `settings.MARVIN_API_KEY`.
  2.  **Marvin Execution:** If enabled, it calls `marvin_classification_manager.get_lead_classification(input_data)`.
  3.  **Result Integration:** The `ClassificationOutput` from Marvin (containing `lead_type`, `reasoning`, and the rich `metadata` with all extracted fields) is used as the basis for the final classification.
  4.  **Post-Processing & Enrichment:**
      - An `assigned_pipeline` is determined based on Marvin's classification.
      - A `confidence` score is calculated (this appears to be a separate heuristic, not directly from Marvin).
      - `requires_human_review` is set (often true after AI processing, for potential oversight).
      - An internal `estimated_value` for the deal is calculated.
      - **Date Normalization:** Crucially, any date fields found within the `metadata` (which originated from Marvin's extraction) are explicitly normalized to the 'YYYY-MM-DD' string format using the `_normalize_date_field_to_yyyy_mm_dd` utility. This acts as a safeguard or correction step, even though Marvin was instructed to provide dates in this format.
  5.  **Fallback:** If Marvin is not enabled, the system falls back to a purely rule-based classification defined in `app/services/classify/rules.py`.

## Summary of Marvin's Role

If enabled, Marvin AI, through the `@marvin.fn classify_lead_with_ai` function, takes on the primary responsibility of:

1.  **Classifying the lead** into predefined categories based on complex rules provided in natural language.
2.  **Extracting a wide array of structured details** from the unstructured call text.
3.  Providing **reasoning** for its classification.

The application then takes this rich, structured output from Marvin, stores the extracted details in the `metadata` field of its classification result, and performs minor additional processing (like date normalization and confidence scoring) before finalizing the `ClassificationResult`. This allows the system to leverage LLMs for nuanced understanding of call data while maintaining a structured approach to lead processing.
