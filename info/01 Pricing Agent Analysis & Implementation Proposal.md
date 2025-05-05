**MEMORANDUM**

To: Stahla Services

From: AI Development Support Date: May 1, 2025

Subject: Analysis and Implementation Proposal for the Stahla Pricing
Agent (Based on V9 Brief)

**Introduction**

This document provides an analysis of the Pricing Agent initiative based
on the provided project documents, primarily "Pricing Agent Project
Brief Version 9" and related SDR integration proposals dated late April
2025. Our focus is on the requirements outlined for Version 9,
specifically achieving rapid, real-time quoting within the
Bland.ai-driven SDR calls.

**Data** **Limitations** **&** **Scope**

Our analysis is based *exclusively* on the Version 9 project brief and
associated documents. These documents describe a Pricing Agent focused
**solely** **on** **quoting** **Stahla's** **services** **and**
**inventory**, using pricing rules defined in internal Google Sheets.

We acknowledge the broader vision mentioned separately (multi-vendor
pricing/inventory collection from 500 locations, complex logistics, NLP
for quote extraction, etc.). However, the V9 architecture and scope
**do** **not** **currently** **address** **these** **advanced**
**requirements**. Implementing that broader vision would necessitate a
fundamentally different architecture, significant data sourcing efforts,
and advanced AI capabilities beyond the V9 plan.

**Scalability** **Assurance:** While the V9 implementation focuses
narrowly on immediate needs for speed and Stahla-specific quoting, the
chosen approach provides a foundation that **does** **not** **prevent**
**future** **scaling** towards the broader vision. Whether integrated or
standalone, the modular design of the pricing logic allows it to be
expanded, refactored, or even replaced in the future. Key patterns like
API-driven interactions (webhooks), caching (Redis), and the use of
scalable technologies (Python, FastAPI) are standard building blocks for
larger systems. Therefore, the V9 work represents a crucial first step,
establishing core functionality and infrastructure that can be built
upon, even though realizing the full multi-vendor marketplace vision

will require substantial dedicated effort and architectural evolution in
subsequent phases.

**Required** **Information** **&** **Access** **(for** **V9**
**Implementation)**

To successfully implement the V9 Pricing Agent as described and ensure
the target speed (\<500ms P95 latency), we require confirmation and
access to the following:

> 1\. **Webhook** **Data** **Confirmation:** Please confirm that the
> Bland.ai Pathway can reliably provide the following data points in the
> /v1/webhook/quote call:
>
> ○ **delivery_location:** A full, accurate address string (Street,
> City, State, Zip).
>
> ○ **trailer_type:** The specific Stahla trailer model ID matching
> internal naming conventions.
>
> ○ **rental_start_date:** In YYYY-MM-DD format. ○ **rental_days:**
> Total rental duration in days.
>
> ○ **usage_type:** Normalized to "commercial" or "event".
>
> ○ **extras:** A list with specific extra_id and qty for each add-on. ○
> **request_id:** A unique identifier.
>
> 2\. **Google** **Sheets** **Access:** Please provide access to the
> definitive Google Sheets containing:
>
> ○ The current pricing tables (equivalent to Appendix A & B in the
> brief). ○ A list of Stahla branch locations (used for nearest branch
> calculation).
>
> 3\. **API** **Keys:** We will need the necessary API keys for:
>
> ○ Google Maps Distance Matrix API(We can use our on for dev/test
> purposes)
>
> ○ Google Sheets API

Access to the definitive Google Sheets containing the pricing tables
(Appendix A & B equivalents) and a list of Stahla branch locations (for
nearest branch calculation) is also essential.

**Recommended** **Technology** **Stack** **(for** **V9)**

The technology stack outlined in the V9 brief and SDR integration
proposal appears well-suited for the defined goals:

> ● **Backend:** Python with FastAPI (integrating the pricing logic
> directly).
>
> ● **Caching:** Redis (for caching pricing catalog, JSON, and Google
> Maps API results). ● **Geo-Services:** Google Maps Distance Matrix API
> (for delivery distance
>
> calculation).
>
> ● **Data** **Source:** Google Sheets API (for fetching pricing rules).
>
> ● **Validation:** Pydantic (for webhook request/response validation).
> ● **Authentication:** API Key security for the webhook.
>
> ● **Observability:** Logging/Monitoring (e.g., Logfire) for
> performance tracking and debugging.

**Implementation** **Models**

Based on the project documents, two primary implementation approaches
were considered:

**1.** **Integrated** **Module** **within** **SDR** **FastAPI**
**Application** **(Chosen** **Approach** **in** **V9)**

> ● **Description:** The pricing logic resides directly within the SDR's
> main FastAPI codebase (e.g., as a pricing Python package). The SDR app
> exposes the /v1/webhook/quote endpoint.
>
> ● **Advantages:**
>
> ○ **Performance:** Eliminates network latency between services,
> maximizing the chance of hitting the \<500ms target.
>
> ○ **Simplicity:** Reduces deployment complexity (one application to
> manage) and simplifies security (no inter-service authentication
> needed beyond the webhook API key).
>
> ○ **Data** **Consistency:** Pricing logic has direct, immediate access
> to the SDR's current lead data context.
>
> ● **Limitations:**
>
> ○ **Tighter** **Coupling:** Changes to the pricing logic require
> redeploying the entire SDR application.
>
> ○ **Resource** **Sharing:** Pricing calculations share resources (CPU,
> memory) with the main SDR application.

**2.** **Standalone** **Pricing** **Microservice**

> ● **Description:** The pricing logic runs as a separate FastAPI
> application with its API (e.g., /quote). The SDR application would
> make an internal API call to this service. (This model was moved away
> from in V9).
>
> ● **Advantages:**
>
> ○ **Decoupling:** Pricing service can be developed, deployed, and
> scaled independently of the SDR application.
>
> ○ **Isolation:** Dedicated resources for pricing calculations.
> Potentially easier to swap out or upgrade independently.
>
> ● **Limitations:**
>
> ○ **Latency:** Introduces network latency for the SDR-to-Pricing
> service call, making the \<500ms target harder to achieve
> consistently.
>
> ○ **Complexity:** Requires managing deployment, monitoring, and
> security (e.g., internal authentication like JWT) for two services.

**Recommendation:** The V9 decision to integrate the pricing logic
directly into the SDR application seems appropriate given the strict
performance requirement for real-time quoting during calls.

**Optimizing** **Location** **Lookup** **Latency**

A key challenge for meeting the \<500ms goal is the potential latency of
the Google Maps Distance Matrix API call, especially for delivery
locations not already cached in Redis.

**Suggestion:** Implement a two-stage webhook process within the
Bland.ai Pathway:

> 1\. **Early** **Location** **Webhook:** As soon as the delivery
> address (service_address) is confirmed during the Bland.ai
> conversation, trigger a *first*, lightweight webhook call to a
> dedicated endpoint in the SDR app (e.g., /v1/webhook/location_lookup).
>
> ○ This endpoint receives *only* the delivery location.
>
> ○ It immediately checks the Redis cache for the pre-calculated
> distance from the nearest branch.
>
> ○ **If** **not** **cached,** it initiates the Google Maps API call
> *asynchronously*
>
> (non-blocking or as a background process) and stores the result in
> Redis upon completion. The webhook returns an immediate 202 Accepted
> response to Bland.ai(This is returned immediately while the background
> process is completed or not to avoid interruptions).
>
> ○ **If** **cached,** it does nothing and returns 200 OK.
>
> 2\. **Main** **Quote** **Webhook:** When the conversation reaches the
> point where a full quote is needed, the *existing* /v1/webhook/quote
> endpoint is called with all the required pricing data (trailer type,
> dates, extras, *and* the location again).
>
> ○ The pricing logic now performs the Redis lookup for the location
> distance. Due to the earlier asynchronous call, there's a high
> probability the result is already cached, making this lookup extremely
> fast.
>
> ○ The rest of the quote (using cached pricing data) is calculated and
> returned synchronously within the target latency.

**Benefits:** This approach decouples the potentially slow external
Google Maps API call from the time-sensitive final quote request. The
distance calculation (which includes the per-mile cost) happens in the
background while Bland.ai continues gathering other details from the
customer. Redis serves as the necessary fast, persistent storage for
this cached location/distance data. We can key the cache using the
normalized delivery location string.

**Conclusion**

The V9 Pricing Agent, integrated into the SDR application, is feasible
and optimized for speed using the proposed stack and caching strategies.
The key is ensuring accurate data mapping from the SDR and eficient
handling of the external Google Maps dependency. The suggested two-stage
location lookup can further mitigate latency risks.

To move forward, we need your decision on:

> 1\. Confirmation of data availability and access (Section: Required
> Information & Access).
>
> 2\. Your preferred implementation model (Integrated vs. Standalone).
> 3. Whether to implement the two-stage location lookup optimization.

.
