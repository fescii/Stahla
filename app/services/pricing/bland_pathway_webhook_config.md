# Bland.ai Pathway: Webhook Node Configuration Draft

This document outlines a draft configuration for a Webhook Node within a Bland.ai Conversational Pathway, designed to fetch a real-time price quote from the Stahla AI SDR FastAPI backend during a call.

## Assumptions

*   Necessary variables (e.g., `product_type`, `num_units`, `rental_duration_days`, `delivery_location_description`, etc.) have been collected in previous nodes of the pathway.
*   These variable names match the field names expected by the `PricingInput` model in the FastAPI backend.
*   Environment variables (`APP_BASE_URL`, `BLAND_WEBHOOK_SECRET`) are configured in Bland.ai.

## Webhook Node Configuration

**1. Node Details:**
   *   **Node Type:** `Webhook`
   *   **Node Name:** `GetRealTimeQuote` (or similar)

**2. Request Configuration:**
   *   **Webhook URL:** `{{env.APP_BASE_URL}}/api/v1/pricing/quote`
       *   *Note:* Replace with the actual URL if not using environment variables.
   *   **Method:** `POST`
   *   **Headers:**
       *   `Content-Type`: `application/json`
       *   `Authorization`: `Bearer {{env.BLAND_WEBHOOK_SECRET}}`
           *   *Note:* Implement validation for this token in the FastAPI endpoint.
   *   **Request Body:**
       *   (Bland.ai automatically sends collected pathway variables as JSON).

**3. Response Handling:**
   *   **Save Response To Variable:** `quote_response`
       *   *Note:* This variable will hold the JSON response (matching the `PriceQuote` model) from the FastAPI endpoint.

**4. Error Handling (Recommended):**
   *   **On Timeout / Error:** Configure a fallback path or message.
       *   *Example Fallback Message Node:* "I'm having trouble calculating the exact quote right now, but our team will follow up with the details shortly."

## Example Usage in Subsequent Script Node

After the `GetRealTimeQuote` Webhook Node runs, use the `quote_response` variable in a "Speak" or "Script" node:

```
Okay, based on what you've told me, the estimated subtotal is {{quote_response.subtotal}} dollars.

{{#if quote_response.is_estimate}}
Please note, this is an estimate because we're still confirming some details like {{#join quote_response.missing_info ", "}}{{/join}}.
{{/if}}

{{#if quote_response.notes}}
A couple of notes on that: {{#each quote_response.notes}} {{this}} {{/each}}
{{/if}}

Does that pricing align with what you were expecting?
```

*   **Note:** Verify the exact template syntax (`{{variable}}`, `{{#if}}`, etc.) in the Bland.ai documentation.

## Key Considerations

1.  **Variable Mapping:** Ensure Bland.ai script variable names match `PricingInput` model fields.
2.  **Security:** Validate the `Authorization` header in the FastAPI endpoint.
3.  **Latency:** The `/api/v1/pricing/quote` endpoint must respond quickly (< 500ms ideally, max 2-3s). Use caching and timeouts.
4.  **Environment Variables:** Use Bland.ai environment variables for URLs/secrets.
5.  **Testing:** Test thoroughly in the Bland.ai sandbox.
