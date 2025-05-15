I'll help you understand how Hubspot is used in this application and provide instructions for creating an API key, access token, and webhook for receiving triggered data from contact creation. Let me first check the relevant Hubspot files and usage in the codebase.

Based on my analysis of the codebase, I can see that this application integrates with HubSpot for lead management and CRM functionality. Let me provide instructions for the client on how to create an API key, access token, and set up a webhook for receiving triggered data from contact creation in HubSpot.

# Instructions for HubSpot Integration with Stahla AI SDR

## 1. Generate a HubSpot Private App Access Token

The application uses HubSpot's API for managing contacts, companies, deals, and more. To set up the integration:

1. **Log in to your HubSpot account**: Go to [https://app.hubspot.com/](https://app.hubspot.com/)

2. **Create a Private App**:

   - Navigate to Settings (gear icon) > Integrations > Private Apps
   - Click "Create private app"
   - Fill in basic details:
     - App name: "Stahla AI SDR"
     - Description: "Integration for Stahla AI SDR application"

3. **Set Required Scopes**:
   Based on the code, the following scopes are needed:

   - `crm.objects.contacts.read` and `crm.objects.contacts.write`
   - `crm.objects.companies.read` and `crm.objects.companies.write`
   - `crm.objects.deals.read` and `crm.objects.deals.write`
   - `crm.objects.owners.read`
   - `crm.schemas.pipeline.read`
   - `crm.associations.read` and `crm.associations.write`

4. **Create App and Copy Access Token**:

   - Click "Create app"
   - After creation, you'll be shown the access token
   - **Important**: This token is shown only once, so copy it immediately

5. **Update Environment Variables**:
   - Open your .env file
   - Set `HUBSPOT_ACCESS_TOKEN="your_access_token_here"`

## 2. Update HubSpot Association Type IDs

The application uses specific association type IDs for connecting different objects in HubSpot. Update these in your .env file:

```
HUBSPOT_ASSOCIATION_TYPE_ID_DEAL_TO_CONTACT=1
HUBSPOT_ASSOCIATION_TYPE_ID_DEAL_TO_COMPANY=2
HUBSPOT_ASSOCIATION_TYPE_ID_COMPANY_TO_CONTACT=3
HUBSPOT_ASSOCIATION_TYPE_ID_TICKET_TO_CONTACT=4
HUBSPOT_ASSOCIATION_TYPE_ID_TICKET_TO_DEAL=5
```

Replace the numbers with the actual association type IDs from your HubSpot account. You can find these in HubSpot's API documentation or by contacting HubSpot support.

## 3. Set Default Pipeline and Stage Names

Configure the default pipeline settings in your .env file:

```
HUBSPOT_DEFAULT_DEAL_PIPELINE_NAME="Sales Pipeline"
HUBSPOT_DEFAULT_TICKET_PIPELINE_NAME="Support Pipeline"
HUBSPOT_DEFAULT_LEAD_LIFECYCLE_STAGE="lead"
```

Modify these values to match your actual HubSpot pipeline and stage names.

## 4. Configure HubSpot Webhook for Contact Creation

To set up a webhook that triggers when new contacts are created:

1. **Navigate to Webhooks Settings**:

   - Go to Settings > Integrations > Webhooks
   - Click "Create webhook"

2. **Configure the Webhook**:

   - Name: "Stahla Contact Creation"
   - Target URL: `https://your-app-domain.com/api/v1/webhook/hubspot`
   - Authentication:
     - Choose "No authentication" (the app handles verification internally)

3. **Select Trigger Event**:

   - Under "Contact properties", select "Create"
   - Optionally, you can also select "Update" if you want to receive updates to contacts

4. **Throttling and Retry Settings**:

   - Set throttling rate as desired (default is fine)
   - Enable retries for failed deliveries

5. **Complete Setup**:
   - Click "Create webhook" to activate

## 5. Testing the Integration

After setting up the HubSpot integration, you can test it using the app's test endpoints:

1. **Test Contact Creation**:

   - Use the `/api/v1/test/contact` endpoint with a sample contact payload
   - This will create a new contact in HubSpot

2. **Test Lead Creation**:

   - Use the `/api/v1/test/lead` endpoint to create a lead
   - This will create a contact, company, and deal in HubSpot

3. **Verify Webhook Reception**:
   - Create a new contact in HubSpot manually
   - Check your application logs to confirm the webhook was received

## Important Notes

1. **Access Token Security**: The HubSpot access token has full permissions for the granted scopes. Keep it secure and never expose it in client-side code.

2. **Token Expiration**: Private App tokens don't expire, but you can revoke and regenerate them as needed for security.

3. **Webhook Verification**: For production, consider implementing signature verification for HubSpot webhooks to ensure the requests come from HubSpot.

4. **Pipeline and Stage IDs**: If you change your HubSpot pipelines, make sure to update the corresponding IDs in your configuration.

5. **Cache TTL**: The application caches HubSpot pipelines, stages, and owners for performance. You can adjust these TTL values if needed:
   ```
   CACHE_TTL_HUBSPOT_PIPELINES=3600
   CACHE_TTL_HUBSPOT_STAGES=3600
   CACHE_TTL_HUBSPOT_OWNERS=3600
   ```

By following these steps, your client will have a fully configured HubSpot integration with the Stahla AI SDR application, including API access and webhook setup for receiving contact creation events.
