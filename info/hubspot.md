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

| Property                                                     | Internal Name                                          | Notes / Confirmation Needed?                                                                                                                               |
| :----------------------------------------------------------- | :----------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------- |
| *What services do you need?                                  | `what_service_do_you_need_`                            | Multiple checkboxes. Options: Restroom Trailer, Shower Trailer, Laundry Trailer, Porta Potty, Trailer Repair / Pump Out, Other. Status: Already Created. |
| How Many Restroom Stalls?                                    | `how_many_restroom_stalls_`                            | Number. Status: Already Created.                                                                                                                           |
| How Many Shower Stalls?                                      | `how_many_shower_stalls_`                              | Number. Status: Already Created.                                                                                                                           |
| How many laundry Units?                                      | `how_many_laundry_units_`                              | Number. Status: Already Created.                                                                                                                           |
| Tell us how we can help                                      | `your_message`                                         | Multi-line text. Status: Already Created.                                                                                                                  |
| Do you have water access available onsite?                   | `do_you_have_water_access_onsite_`                     | Single-line text. Status: Already Created.                                                                                                                 |
| Do you have power access available onsite?                   | `do_you_have_power_access_onsite_`                     | Single-line text. Status: Already Created.                                                                                                                 |
| Check this box if you need the ADA standards                 | `ada`                                                  | Single Checkbox. Status: Already Created.                                                                                                                  |
| *How Many Portable Toilet Stalls?                            | `how_many_portable_toilet_stalls_`                     | Number. Status: Already Created.                                                                                                                           |
| *Event or Job Address                                        | `event_or_job_address`                                 | Single-line text. Mandatory: Yes. Status: Already Created.                                                                                                 |
| *Postal code                                                 | `zip`                                                  | Single line text. Status: Already Created.                                                                                                                 |
| *City                                                        | `city`                                                 | Single-line text. Status: Already Created.                                                                                                                 |
| Street Address                                               | `address`                                              | Single line text. Status: Already Created.                                                                                                                 |
| *Event start date                                            | `event_start_date`                                     | Date Picker. Mandatory: Yes. Status: Already Created.                                                                                                      |
| Event end date                                               | `event_end_date`                                       | Date Picker. Status: Already Created.                                                                                                                      |
| *First name                                                  | `firstname`                                            | Single-line text. Mandatory: Yes. Status: Already Created.                                                                                                 |
| *Last name                                                   | `lastname`                                             | Single-line text. Mandatory: Yes. Status: Already Created.                                                                                                 |
| *Phone number                                                | `phone`                                                | Phone number. Mandatory: Yes. Status: Already Created.                                                                                                     |
| *Email                                                       | `email`                                                | Single line text. Mandatory: Yes. Status: Already Created.                                                                                                 |
| *Message                                                     | `message`                                              | Multi-line text. Status: Already Created.                                                                                                                  |
| *I consent to receive texts on the phone number provided     | `by_submitting_this_form_you_consent_to_receive_texts` | Single checkbox. Status: Already Created.                                                                                                                  |
| AI Call Summary                                              | `ai_call_summary`                                      | Multi-line text. Mandatory: Yes. Status: Needs to be Created. Description: Summary of the AI-qualified call details.                                      |
| AI Call Sentiment                                            | `ai_call_sentiment`                                    | Single line text. Status: Needs to be Created. Description: Assessment of prospect sentiment/tone.                                                         |
| Call Recording URL                                           | `call_recording_url`                                   | Single-line text. Status: Needs to be Created. Description: URL link to the recorded call                                                                  |
| Call Summary                                                 | `call_summary`                                         | Multi-line text. Status: Needs to be Created. Description: AI-generated summary of what was discussed on the call                                          |

---

**Lead Properties:**

| Property                             | Internal Name                         | Notes / Confirmation Needed?                                                                                                                               |
| :----------------------------------- | :------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Project Category                     | `project_category`                    | Single line text. Mandatory: Yes. Status: Needs to be Created. Description: Type of inquiry or project (e.g. Event, Construction, Facility, Disaster Relief, Other) for this lead; used to tailor qualification flow and branching logic. |
| Units Needed (Description)           | `units_needed`                        | Multi-line text. Mandatory: Yes. Status: Needs to be Created. Description: Summary of quantity and type of units required (e.g.: “2-stall restroom trailer and 10 portable toilets”). |
| Expected Attendance/Users            | `expected_attendance`                 | Number. Status: Needs to be Created. Description: Number of people the facilities need to support (for events or project capacity).                         |
| ADA Accessible Required              | `ada_required`                        | Single checkbox. Mandatory: Yes. Status: Needs to be Created. Description: Indicates if ADA-compliant (handicap accessible) facilities are needed.         |
| Additional Services Needed           | `additional_services_needed`          | Multi-line text. Status: Needs to be Created. Description: Other services or equipment needed beyond core rentals (e.g. tent, fencing, generator, water supply, dumpster). |
| Other Facilities On-site             | `onsite_facilities`                   | Single checkbox. Status: Needs to be Created. Description: Whether there are existing facilities at the site.                                              |
| Rental Start Date                    | `rental_start_date`                   | Date picker. Status: Needs to be Created. Description: When the unit(s) will be needed on site.                                                            |
| Rental End Date                      | `rental_end_date`                     | Date picker. Status: Needs to be Created. Description: Expected end date or pickup date for the rental.                                                    |
| Site Working Hours                   | `site_working_hours`                  | Single-line text. Status: Needs to be Created. Description: Working hours or access times at the site.                                                     |
| Weekend Service Needed               | `weekend_service_needed`              | Single checkbox. Status: Needs to be Created. Description: Indicates if service is required over the weekend.                                              |
| Cleaning/Restocking Needed           | `cleaning_service_needed`             | Single checkbox. Status: Needs to be Created. Description: Indicates prospect needs cleaning or restocking service.                                        |
| On-site Contact Name                 | `onsite_contact_name`                 | Single-line text. Status: Needs to be Created. Description: Alternate on-site contact name for coordination.                                               |
| On-site Contact Phone                | `onsite_contact_phone`                | Phone number. Status: Needs to be Created. Description: Phone number for the on-site contact.                                                              |
| Site Ground Surface Type             | `site_ground_type`                    | Single-line text. Status: Needs to be Created. Description: Ground/terrain at the drop-off location (e.g. Concrete, Gravel, Grass).                         |
| Site Obstacles/Access Notes          | `site_obstacles`                      | Multi-line text. Status: Needs to be Created. Description: Notes on access limitations or obstacles at the site.                                           |
| Distance to Water Source (ft)        | `water_source_distance`               | Number. Status: Needs to be Created. Description: Approximate distance from unit location to nearest water source.                                         |
| Distance to Power Source (ft)        | `power_source_distance`               | Number. Status: Needs to be Created. Description: Approximate distance from unit location to nearest power source.                                         |
| Within Local Service Area            | `within_local_service_area`           | Single checkbox. Mandatory: Yes. Status: Needs to be Created. Description: Checked if location is within ~3 hours of a service hub.                         |
| Consent to Partner Referral          | `partner_referral_consent`            | Single checkbox. Status: Needs to be Created. Description: Indicates if prospect agreed to share info with partner companies.                                |
| Needs Human Follow-Up                | `needs_human_follow_up`               | Single checkbox. Status: Needs to be Created. Description: Flag for AI to escalate leads needing human clarification.                                      |
| Quote Urgency                        | `quote_urgency`                       | Single line text. Mandatory: Yes. Status: Needs to be Created. Description: How quickly the prospect wants a quote or follow-up.                           |
| AI Lead Type                         | `ai_lead_type`                        | Single line text. Status: Needs to be Created. Description: AI‑determined category of the lead (e.g. Event, Construction, etc.)                             |
| AI Classification Reasoning          | `ai_classification_reasoning`         | Multi-line text. Status: Needs to be Created. Description: Explanation of the AI’s logic in classifying this lead                                          |
| AI Classification Confidence         | `ai_classification_confidence`        | Number (decimal). Status: Needs to be Created. Description: Confidence score (0–1) for the AI’s classification                                             |
| AI Routing Suggestion                | `ai_routing_suggestion`               | Single-line text. Status: Needs to be Created. Description: Pipeline or stage the AI recommends routing this lead into                                     |
| AI Intended Use                      | `ai_intended_use`                     | Single line text. Status: Needs to be Created. Description: AI‑identified intended purpose for this inquiry                                                |
| AI Qualification Notes               | `ai_qualification_notes`              | Multi-line text. Status: Needs to be Created. Description: Key notes from the AI’s qualification assessment                                                |
| Number of Stalls (from Call/Form)    | `number_of_stalls`                    | Number (integer). Status: Needs to be Created. Description: How many stalls were requested (from call or form)                                             |
| Event Duration Days (from Call/Form) | `event_duration_days`                 | Number (integer). Status: Needs to be Created. Description: Number of days the prospect needs the units                                                    |
| Guest Count Estimate (from Call/Form)| `guest_count_estimate`                | Number (integer). Status: Needs to be Created. Description: Estimated attendee count (optional)                                                            |
| AI Estimated Value                   | `ai_estimated_value`                  | Number (currency). Status: Needs to be Created. Description: AI‑calculated estimate of deal value                                                          |