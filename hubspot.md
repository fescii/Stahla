# Form Input: from the website (Example Submission)

What service do you need?  
Porta Potty

How Many Portable Toilet Stalls?  
1

Event or Job Address  
3035 Whitmore Street, Omaha, NE, USA

Postal code  
68112

City  
Omaha

Event start date  
5/25/25

Event end date  
5/25/25

First name  
Carolyn

Last name  
Lee

Phone number  
4022083411

Email  
crawfordlee52@hotmail.com

I consent to receive texts on the phone number provided  
Yes

---

**Contact Properties:**

*Properties marked with `*` are likely relevant inputs for the API based on the form.*

| Property                       | Internal name                         | Notes / Confirmation Needed?                                  |
| :----------------------------- | :------------------------------------ | :------------------------------------------------------------ |
| *First Name                    | `firstname`                           | Standard                                                      |
| *Last Name                     | `lastname`                            | Standard                                                      |
| *Phone Number                  | `phone`                               | Standard                                                      |
| *City                          | `city`                                | Standard                                                      |
| Company Name                   | `company`                             | Standard                                                      |
| Company Size                   | `company_size`                        | Standard                                                      |
| Lifecycle stage                | `lifecyclestage`                      | Standard (Radio Select)                                       |
| *Event Or Job Address          | `event_or_job_address`                | Custom? Confirm name.                                         |
| Lead Status                    | `hs_lead_status`                      | Standard (Radio Select)                                       |
| Original Traffic Source        | `hs_analytics_source`                 | Standard                                                      |
| Latest Traffic Source          | `hs_latest_source`                    | Standard                                                      |
| Record source                  | `hs_object_source_label`              | Standard (Dropdown select)                                    |
| How Many Shower Stalls?        | `how_many_shower_stalls_`             | Custom? Confirm name. (Relevant if selected in Service Needed)|
| How Many Restroom Stalls?      | `how_many_restroom_stalls_`           | Custom? Confirm name. (Relevant if selected in Service Needed)|
| How many laundry Units?        | `how_many_laundry_units_`             | Custom? Confirm name. (Relevant if selected in Service Needed)|
| How Many ADA Restroom Stalls?  | `how_many_ada_restroom_stalls_`       | Custom? Confirm name. (Relevant if selected in Service Needed)|
| How many ADA Compliant Showers?| `how_many_ada_compliant_showers_`     | Custom? Confirm name. (Relevant if selected in Service Needed)|
| *How Many Portable Toilet Stalls?| `how_many_portable_toilet_stalls_`    | Custom? Confirm name.                                         |
| *Email                         | `email`                               | Standard                                                      |
| *Postal Code                   | `zip`                                 | Standard? Confirm name.                                       |
| *Message                       | `message`                             | Standard? Confirm name.                                       |
| *Service Needed                | `stahla_service_needed`               | **Custom - Needs Creation/Confirmation**                      |
| *Event Start Date              | `stahla_event_start_date`             | **Custom - Needs Creation/Confirmation** (Date Type)          |
| *Event End Date                | `stahla_event_end_date`               | **Custom - Needs Creation/Confirmation** (Date Type)          |
| *Text Consent                  | `stahla_text_consent`                 | **Custom - Needs Creation/Confirmation** (Boolean Type)       |

---

**Deal Properties:**

*Properties marked with `*` are likely set/updated by the API.*
*Properties marked with `**` are suggested new properties for AI/Call results.*

| Property                             | Internal name                         | Notes / Confirmation Needed?                                  |
| :----------------------------------- | :------------------------------------ | :------------------------------------------------------------ |
| Deal Name                            | `dealname`                            | Standard - Set by Workflow/API                                |
| Amount                               | `amount`                              | Standard - *See Note Below Re: Budget Estimation*             |
| Close Date                           | `closedate`                           | Standard - Potentially set by API based on end date?          |
| *Pipeline                            | `pipeline`                            | Standard (Radio Select) - Set by API/Workflow                 |
| Deal Owner                           | `hubspot_owner_id`                    | Standard - Set by API/Workflow                                |
| Commercial/Event                     | `commercial_event`                    | Custom? (Dropdown Select) - Potentially set by API?           |
| *Deal Stage                          | `dealstage`                           | Standard (Radio Select) - Set by API/Workflow                 |
| *Start Date                          | `start_date`                          | Standard (Date Type) - Copied from Contact Property           |
| *End Date                            | `end_date`                            | Standard (Date Type) - Copied from Contact Property           |
| Deal Duration                        | `deal_duration`                       | Standard? Calculated?                                         |
| *Deal Address                        | `deal_address`                        | Standard? Copied from Contact Property                        |
| Last Contacted                       | `notes_last_contacted`                | Standard - Updated by HubSpot                                 |
| Deal Type                            | `dealtype`                            | Standard (Radio Select) - Set by API/Workflow                 |
| Priority                             | `hs_priority`                         | Standard (Dropdown select) - Potentially set by API?          |
| Lead Status                          | `hs_lead_status`                      | Standard (Radio Select) - Potentially set by API?             |
| **AI Lead Type                       | `stahla_ai_lead_type`                 | **Custom - Needs Creation** (Text/Dropdown)                   |
| **AI Classification Reasoning        | `stahla_ai_reasoning`                 | **Custom - Needs Creation** (Text - Multi-line)               |
| **AI Classification Confidence       | `stahla_ai_confidence`                | **Custom - Needs Creation** (Number - Float)                  |
| **AI Routing Suggestion (Pipeline)   | `stahla_ai_routing_suggestion`        | **Custom - Needs Creation** (Text)                            |
| **AI Requires Human Review           | `stahla_ai_requires_review`           | **Custom - Needs Creation** (Boolean)                         |
| **AI Is Local                        | `stahla_ai_is_local`                  | **Custom - Needs Creation** (Boolean)                         |
| **AI Intended Use                    | `stahla_ai_intended_use`              | **Custom - Needs Creation** (Text/Dropdown)                   |
| **AI Qualification Notes             | `stahla_ai_qualification_notes`       | **Custom - Needs Creation** (Text - Multi-line)               |
| **Call Recording URL                 | `stahla_call_recording_url`           | **Custom - Needs Creation** (Text - URL)                      |
| **Call Summary                       | `stahla_call_summary`                 | **Custom - Needs Creation** (Text - Multi-line)               |
| **Call Duration (Seconds)            | `stahla_call_duration_seconds`        | **Custom - Needs Creation** (Number - Integer, Optional)      |
| **Number of Stalls (from Call/Form)  | `stahla_stall_count`                  | **Custom - Needs Creation** (Number - Integer)                |
| **Event Duration Days (from Call/Form)| `stahla_event_duration_days`          | **Custom - Needs Creation** (Number - Integer)                |
| **Guest Count (from Call)            | `stahla_guest_count`                  | **Custom - Needs Creation** (Number - Integer)                |
| **ADA Required (from Call/Form)      | `stahla_ada_required`                 | **Custom - Needs Creation** (Boolean)                         |
| **Power Available (from Call)        | `stahla_power_available`              | **Custom - Needs Creation** (Boolean)                         |
| **Water Available (from Call)        | `stahla_water_available`              | **Custom - Needs Creation** (Boolean)                         |
| **AI Estimated Value (Optional)      | `stahla_ai_estimated_value`           | **Custom - Needs Creation** (Number - Currency, Optional)     |

**Note on Budget/Amount:** The call script advises against estimating budget. The current classification code *does* estimate a value. Recommend discussing with the client whether to:
a) Remove the estimation logic and not set the standard `amount` property.
b) Keep the estimation but store it in the suggested custom property `stahla_ai_estimated_value` instead of `amount`.