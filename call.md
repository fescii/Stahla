AUTOMATED PHONE CALL SCRIPT:
TABLE OF CONTENTS
• Main Flow.
• Call Back Flow.
• PATHS.
• SUBFLOWS (S).
• PROCESSES.
• PRODUCTS PATHS.
• PRODUCTS QUESTIONS.
• OBJECTION HANDLING & FAQ.
• VALUE PROPOSITION & ELEVATOR PITCH.
• PERSONALIZATION & RAPPORT BUILDING.
• CLEAR NEXT STEPS & FOLLOW‑UP.
• DATA PRIVACY & COMPLIANCE.
• SCRIPT FLEXIBILITY & ADAPTABILITY.
• CALL METRICS & QUALITY CONTROL.
• TONAL GUIDELINES & VALUE ALIGNMENT.
• Identified Issues & Suggested Corrections.

MAIN FLOW.
Call In
• Warm Greeting:
– Begin with a friendly and engaging introduction. Consider asking, “How can we best support
your project or event today?” to invite an open conversation.
• Collect Contact Information:
– "To get started, could I please get your first and last name?"
– "And what's the best email address to reach you at?"
– "What phone number are you calling from, or what's the best number to call you back on?"
– Capture any existing CRM or context information to quickly verify if this is an existing lead.
• Identify Need and Context:
– Ask Why They Are Calling: “Could you tell me a bit about why you're calling today and what specific needs or challenges you're facing?”
– **Clarify Intended Use:** "And what is the primary use for our services? For example, is it for a construction site, a special event like a wedding or festival, disaster relief, or a long-term facility need?" (Helps determine `stahla_ai_intended_use`)
– **Collect Full Address:** "What is the full address, including street, city, state, and zip code, where the services will be needed? This helps us determine availability and logistics." (Needed for `stahla_ai_is_local` and routing)
– **Determine Product Type:** "Are you primarily looking for portable toilets or larger restroom/shower trailers?"
– **Gather Initial Scale Info:**
    - If Portable Toilets: "Roughly how many portable toilet stalls do you think you'll need?" (Collects `stahla_stall_count` early)
    - If Trailers: "Do you have an idea of the number of stalls or stations you might need in the trailer(s)?" (Helps determine scale and `stahla_stall_count`)
• Identify Which “Lead Type” They Are (Use collected info: Intended Use, Address/Local, Product Type, Stall Count):
1.​ Event / Porta Potty​
2.​ Construction / Porta Potty​
3.​ Small Event / Trailer / Local​
4.​ Small Event / Trailer / Not Local​
5.​ Large Event / Trailer / Local​
6.​ Large Event / Trailer / Not Local​
7.​ Disaster Relief / Trailer / Local​
8.​ Disaster Relief / Trailer / Not Local​
9.​ Construction / Company Trailer / Local​
10.​Construction / Company Trailer / Not Local​
11.​Facility / Trailer / Local​
12.​Facility / Trailer / Not Local
– Provide examples if needed to ensure the agent accurately classifies the lead. The system should use the address and stall count to help determine local status and potential size category.
• Ask Additional Clarification Questions Based on Their “Lead Type”:
– When responses are vague, use follow‑up questions to gain detailed context (e.g., specific product requirements, project scope).
• Action: Create an SOP for Sorting Leads:
• Integrate a Brief Value Proposition Introduction:
– Example: “At Stahla, we pride ourselves on providing customized, reliable solutions that
keep your event or project running smoothly.”
– Note: Act as the expert and tailor this pitch slightly based on the prospect’s expressed
needs (e.g., event, construction).
• Follow Path A.

CALL BACK FLOW.
a. On Callback:
– Repeat any missing questions from the original flow (Main Flow) and re‑classify via Path A
logic.
– Double-check contact details and confirm the preferred follow‑up method.
b. Confirm Follow‑Up Details:
– Explicitly schedule the next interaction and confirm communication channels (phone, email,
or in‑person meeting).

PATHS.
Path A – When the Client Chooses from the Existing Leads in the System:
●​ Case a: Event | Porta Potty​
​
• Follow Event Subflow: SA​
​
• Process: PA (corrected from PC to reflect in‑area events)​
●​ Case b: Construction | Porta Potty​
​
• Follow the Event Subflow: SB​
​
• Process: If local → Process PA; if not → Process PB (assignment added per
corrections)​
●​ Case c: Small Event | Trailer | Local (<$10,000)​
​
• Follow Event Subflow: SA​​
• Process: PC​
●​ Case d: Small Event | Trailer | Not Local (<$10,000)​
​
• Follow Event Subflow: SA​
​
• Process: PA​
●​ Case e: Large Event | Trailer | Local (≥$10,000)​
​
• Follow Event Subflow: SA​
​
• Process: PA​
●​ Case f: Large Event | Trailer | Not Local (>$10,000)​
​
• Follow Event Subflow: SA​
​
• Process: PB​
●​ Case g: Disaster Relief | Trailer | Local (>$10,000)​
• Follow the Event Subflow: SB​
​
• Process: PA
●​ Case h: Disaster Relief | Trailer | Not Local (>$10,000)
​
• Follow the Event Subflow: SB​
​
• Process: PB​
●​ Case i: Construction Company | Trailer | Local (>$5,000)​
​
• Follow the Event Subflow: SB​
​
• Process: PA​
●​ Case j: Construction Company | Trailer | Not Local (>$5,000)​
​
• Follow the Event Subflow: SB​​
• Process: PB​
●​ Case k: Facility | Trailer | Local (>$10,000)​
​
• Follow the Event Subflow: SB​
​
• Process: PA​
●​ Case l: Facility | Trailer | Not Local (>$10,000)​
​
• Follow the Event Subflow: SB​
​
• Process: PB​
Note: “Local” is defined as “within 3 hours of our service hubs (Denver, CO; Omaha, NE; Kansas City,
KS).” (Address collected in Main Flow determines this)

SUBFLOWS (S).
Event Subflow: SA
a. Event Duration:
– “How many days is your event?” (Collects `stahla_event_duration_days`)
• If 1 day, record as a 1‑day event.
• If 2 or more days, ask: “How many total hours will the (product type(s)) be needed?”
– If <8 total hours, treat as a 1‑day event.
– If ≥8 hours, discuss the need for extra services (waste tank pumping, fresh water fill,
cleaning, restocking).
Tip: Confirm if there will be any service gaps before the next day.
b. Attendance:
– “Approximately how many people will be attending the event at its peak?” (Collects `stahla_guest_count`)
c. On-site Facilities:
– “Are there any existing restroom or shower facilities available on-site for guest use?” (Clarified question)
d. ADA Requirements:
– “Will you have anyone on site requiring wheelchair access or using a walker? Do you need ADA-compliant (handicap accessible) facilities?” (Collects `stahla_ada_required`)
• If Yes, note the need for handicap accessible products.
• If No, record accordingly.
e. Additional Products:
– “Do you need any other products? (E.g., tent, temporary fencing, generator power.)”
Note: Ensure a comprehensive view of their event needs.

Event Subflow: SB (Commercial Construction Project Subflow)
a. Onsite Contact:
– “Are you the onsite contact, or do you have a different onsite point of contact?”
b. Working Hours and Availability:
– “What are the typical working hours at the project location?”
– Ask if services (waste tank pumping, fresh water fill, cleaning, restocking) are needed over
the weekend.
c. ADA Requirement:
– “Are you required by regulation or site policy to have handicap accessible (ADA) product(s)?” (Collects `stahla_ada_required`)
d. Capacity Requirements:
– “How many workers or personnel do the (product(s)) need to support on an average day?” (Helps confirm `stahla_guest_count` equivalent for construction)
e. Additional Facilities:
– “Are there any existing restroom or shower facilities available on-site for worker use?” (Clarified question)
f. Other Products:
– “Do you need any other products?”
• Options include: Dumpsters, office trailers, temporary fencing, generator power, portable
fresh water
g. Compliance Check:
– Conduct internal research of OSHA, federal, state, county, and city rules (e.g., hot water,
ADA, stall specifications).
h. Cleaning & Restocking:
– “Is cleaning and restocking required, or do you have someone onsite?”
Note: usually if there is a janitorial crew onsite that cleans and restocks the onsite facilities,
that is the best option. If they don’t have that onsite, we can help provide cleaning and
restocking.

PROCESSES.
Process: PA (For Stahla Services)
a. Recap and Qualify:
– Recap lead needs and potential solutions; ask:
• “How soon would you like the quote?”
• “When do you plan on making the decision to rent the (product(s))?”
• “Is there anything else I can help with?”
• “Thank you so much for reaching out. We’ll get you pricing and additional information as
soon as possible.”
Tip: Emphasize a clear timeline and next steps (actively working to get them pricing and
solutions asap).
b. HubSpot Actions (Using API Webhook):
– Create a full conversation summary and recording.
– Fill out lead details.
– Create a Deal in the Stahla Services Pipeline
– Assign the Deal to the Stahla Services Sales Team.
– Notify the Sales Team.
Note: Complete these steps immediately for data accuracy.

Process: PB (For Stahla Logistics)
a. Recap and Qualify:
– Recap lead needs and potential solutions; ask:
• “How soon would you like the quote?”
• “When do you plan on making the decision to rent the (product(s))?”
• “Is there anything else I can help with?”
• “Thank you so much for reaching out. We’ll get you pricing and additional information as
soon as possible.”
Tip: Emphasize a clear timeline and next steps (actively working to get them pricing and
solutions asap).
b. HubSpot Actions (Using API Webhook):
– Create a full conversation summary and recording.
– Fill out lead details.
– Create a Deal in the Stahla Logistics Pipeline
– Assign the Deal to the Stahla Logistics Sales Team.
– Notify the Sales Team.

Process: PC (For Stahla Leads – Outside Service Area)
a. Service Area Notification:
– Inform the prospect that they are outside our service area for the (product(s)).
b. Referral Offer:
– Offer a partner referral by asking: “We have parter companies in your area. Would it be
helpful if we shared all your info with our partner companies for to try and get you multiple
quotes on this?”
• If No, politely wrap up the conversation; mark lead stage as “disqualified” and note the
reason as “not a good fit.”
• If Yes, quickly recap lead needs, follow process PC c. and ask follow‑up questions as per
Process PA.
c. (If “Yes” on b.) HubSpot Actions (Using API Webhook):
– Create a full conversation summary and recording.
– Fill out lead details.
– Mark Lead Stage as Disqualified and note the reason as Lead Sales
– Add the Contact to the List “Stahla Leads - Upload List”

PRODUCTS PATHS.
Specialty Trailer: GA
a. Product Options:
– The client can choose from:
• Restroom Trailer
• Shower Trailer
• Other Specialty Trailer
b. For Restroom or Shower Trailer:
– Confirm/Ask: "Earlier you mentioned needing about [X] stalls/stations. Is that correct, or do you have a more specific number in mind now?" (Confirms `stahla_stall_count` if needed)
– Ask: “Do you know if you need Handicap Accessible Solutions (ADA)?” (Confirms `stahla_ada_required` if not already clear)
c. For Other Specialty Trailer:
– Offer options such as: Bunk House Trailer, Laundry Trailer, Decontamination Trailer. If not
any of these, note which other specialty trailer they are looking for.
– Confirm/Ask: “How many stations are you needing?” (Confirms `stahla_stall_count` equivalent)
d. Next Steps:
– Proceed to Specialty Trailer Questions (PAQ).

Portable Toilet: GB
– Confirm/Ask: "Earlier you mentioned needing about [X] stalls. Is that correct, or do you have a more specific number now?" (Confirms `stahla_stall_count` if needed)
– Proceed to Portable Toilet Questions (PBQ).

PRODUCTS QUESTIONS.
Specialty Trailer Questions: PAQ
a. Delivery Location:
– “Are there any low overhanging trees or obstacles below 13 feet on the way to the specific placement spot?”
– “Is the ground at the placement spot level (flat)?”
– “Is the surface cement, gravel, dirt, or grass?”
b. Delivery Address:
– “Is the delivery address [Confirm Address from Main Flow] a business, residence, or other type of location?”
c. Duration:
– “When are the ideal delivery and pickup dates?” (Helps confirm `stahla_event_duration_days`)
d. Power Availability:
– “Is standard electrical power available on site within about 200 feet of where the trailer will be placed?” (Collects `stahla_power_available`)
• If yes, ask: “Do you plan on needing the cord placed over a walking or driving path?”
(Offer cord ramps if necessary.)
• “How far is the power source?” (Provide ranges: <50’; 50’–100’; 100’–200’; over 200 feet.)
• If no, ask if they’d like generator options.
e. Water Availability:
– “Is a standard water hookup (like a garden hose spigot) available on site within about 100 feet?” (Collects `stahla_water_available`)
• If yes, ask: “How far is the water source?” and “Do you require hose placement over a
walking or driving path?”
• If no, explain water delivery options (e.g., using onboard tanks, requires service for refills).

Portable Toilet Questions: PBQ
a. Number of Stalls:
– Confirm required number of stalls (already asked in Main Flow/Product Paths).
b. Delivery Location:
– “Are there any specific obstacles (e.g., low trees, uneven ground, stairs) near the exact spot where the toilets should be placed?”
c. Delivery Address:
– “Is the delivery address [Confirm Address from Main Flow] a business, residence, or other type of location?”
d. Duration:
– “When are the ideal delivery and pickup dates?” (Helps confirm `stahla_event_duration_days`)

OBJECTION HANDLING & FAQ.
a. Common Objections:
– Pricing Concerns: “We understand budget constraints; let’s review options that can fit your
needs without compromising service quality.”
– Service Area Limitations: “Local” is defined as “within 3 hours of our service hubs (Denver, CO;
Omaha, NE; Kansas City, KS).”
– Product Suitability: “Based on your input, our (specific product) is ideally suited to your
project requirements.”
Note: (to the ai development team) reference stahla.com for (specific product) or (product
model) options (ie: 2 stall restroom trailer)
– Additional Tip: If the conversation becomes too technical or requires further detail, escalate
to a senior expert (human in the loop).
b. FAQ Prompts:
– Prepare reference answers for technical details, installation, and contract terms.
– Ensure SDRs have quick-access FAQ cards or a menu within the CRM for fast reference.

VALUE PROPOSITION & ELEVATOR PITCH.
a. Key Benefits:
– Emphasize reliability, quality, and tailored solutions.
– Highlight unique features such as customizable options and an exceptional service track
record.
b. Elevator Pitch:
– “Stahla.com delivers unparalleled [product/service] solutions that ensure your event or
construction project is executed with precision, backed by our commitment to excellence and
community values.”
– Reminder: Adapt your pitch based on the prospect’s expressed needs.

PERSONALIZATION & RAPPORT BUILDING.
a. Warm, Genuine Introduction:
– Start with a friendly greeting and a brief introduction that sets a welcoming tone.
b. Rapport Prompts:
– Ask open‑ended questions about the prospect’s event or project, for example: “Can you tell
me more about your upcoming project?”
– Use CRM data to reference past interactions or specific details.
– act as the “expert” or “guide” so this can be a helpful call for the lead and they can get most
of their questions answered in an efficient way
c. Pre-Call Research:
– Quickly review available CRM data to personalize conversation points and show informed
interest.

CLEAR NEXT STEPS & FOLLOW‑UP.
a. Confirm Next Steps:
– Examples: “Let’s schedule a follow‑up call to finalize details.”
– “I will send over a tailored proposal by [specific date/time].”
b. Clarify Communication Channels:
– Confirm if follow‑up will be via email, phone, or an in‑person meeting.
c. Record and Confirm:
– Update HubSpot immediately with next steps and follow‑up schedules to ensure complete
documentation.

DATA PRIVACY & COMPLIANCE.
a. Consent and Recording:
– Inform the prospect: “This call may be recorded for quality assurance in compliance with
privacy regulations.”
b. Data Usage Disclaimer:
– Briefly explain how their data will be used and securely stored.
– Offer an opt‑out option if a prospect expresses concerns.
c. Explicit Consent:
– Ask for permission before recording or when collecting personal data.

SCRIPT FLEXIBILITY & ADAPTABILITY.
a. Guideline, Not a Verbatim Script:
– Encourage SDRs to adapt the conversation naturally while ensuring core messaging
remains intact.
b. Documentation:
– Record any deviations from the script and include feedback for continuous improvement.
c. Tone Modulation:
– Adjust questions and phrasing based on the prospect’s responses while maintaining overall
consistency.
– Practice role‑playing scenarios during training sessions for enhanced adaptability.

CALL METRICS & QUALITY CONTROL.
a. Post-Call Checklist:
– Confirm that all required information has been captured.
– Verify that any objections were handled effectively and next steps were clearly defined.
b. Data Recording:
– Log call details and metrics in HubSpot for performance tracking.
c. Continuous Improvement:
– Use call insights and agent feedback to update training materials and refine the script
regularly.

TONAL GUIDELINES & VALUE ALIGNMENT.
a. Professional and Empathetic Tone:
– Maintain clear and direct communication that feels both warm and respectful.
b. Value-Driven Language:
– Integrate subtle statements reflecting our commitment to service excellence, integrity, and
community values.
Example: “At Stahla, we serve our community with honesty, dedication, and integrity.”
c. Adaptable Messaging:
– Ensure that your language is straightforward yet empathetic to resonate with diverse leads.

Identified Issues & Suggested Corrections
• Clarification & Consistency:
– Ensure that lead type classification and service area definitions are clearly communicated
throughout the script.
– Reinforce next steps with explicit confirmation from the prospect.
• Enhanced Objection Handling:
– Provide additional sample responses and triggers for escalation when deeper technical
queries arise.
• Agent Guidance:
– Use visual aids (such as decision trees or flowcharts) during training to help agents
navigate the script.
– Encourage prompt documentation in HubSpot for timely follow‑up and continuous
performance improvement.

**Note on AI Estimation (`stahla_ai_estimated_value`):** While the script avoids asking for the customer's budget directly, the information collected (Lead Type, Stall Count, Duration, Attendance/Capacity, ADA needs, Power/Water for trailers) should provide the AI with sufficient data points to potentially generate an estimated value if required by the client's chosen process.
