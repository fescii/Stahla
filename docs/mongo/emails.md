# MongoDB Emails Collection Documentation

## Overview

The emails collection manages email tracking and automation for the Stahla AI SDR system. It provides comprehensive email lifecycle management, tracking, and analytics for customer communications.

## Collection Structure

**Collection Name**: `emails`  
**Operations Class**: `EmailsOperations` (app/services/mongo/emails/operations.py)  
**Document Model**: `EmailDocument` (app/models/mongo/emails.py)  

## Document Schema

### Core Fields

- **id** (string): Unique email identifier
- **contact_id** (string): HubSpot contact ID
- **message_id** (string): Email message ID
- **thread_id** (string): Email thread identifier
- **subject** (string): Email subject line
- **status** (string): Email status (pending, sent, delivered, failed)
- **direction** (string): Email direction (inbound, outbound)
- **category** (string): Email category (follow_up, quote, support)
- **created_at** (datetime): Record creation timestamp
- **updated_at** (datetime): Last update timestamp

### Extended Fields

- **from_email** (string): Sender email address
- **to_email** (string): Recipient email address
- **body** (string): Email body content
- **html_body** (string): HTML email body
- **attachments** (array): Email attachments
- **sent_at** (datetime): Email sent timestamp
- **delivered_at** (datetime): Email delivered timestamp
- **opened_at** (datetime): Email opened timestamp
- **clicked_at** (datetime): Email clicked timestamp

## Core Operations

### CRUD Operations

#### create_email(email_data: Dict[str, Any]) -> Optional[str]

Creates a new email record with validation and automatic timestamp generation.

#### update_email(email_id: str, update_data: Dict[str, Any]) -> bool

Updates an existing email with automatic updated_at timestamp.

#### get_email(email_id: str) -> Optional[Dict[str, Any]]

Retrieves a single email by ID with MongoDB _id conversion.

#### delete_email(email_id: str) -> bool

Soft or hard deletion of email records.

### Contact-Based Queries

#### get_emails_by_contact(contact_id: str, limit: int = 10) -> List[Dict[str, Any]]

Retrieves all emails for a specific contact.

#### get_emails_by_thread(thread_id: str, limit: int = 50) -> List[Dict[str, Any]]

Retrieves all emails in a specific thread.

## Pagination Methods

All pagination methods use hardcoded PAGINATION_LIMIT = 10 with offset calculation.

### Temporal Sorting

#### get_recent_emails(offset: int = 0) -> List[EmailDocument]

Retrieves emails ordered by created_at (newest first).

#### get_oldest_emails(offset: int = 0) -> List[EmailDocument]

Retrieves emails ordered by created_at (oldest first).

### Status-Based Filtering

#### get_emails_by_status(status: str, offset: int = 0) -> List[EmailDocument]

Retrieves emails filtered by status with pagination.

#### get_successful_emails(offset: int = 0) -> List[EmailDocument]

Retrieves emails with successful delivery status.

#### get_failed_emails(offset: int = 0) -> List[EmailDocument]

Retrieves emails with failed status.

#### get_pending_emails(offset: int = 0) -> List[EmailDocument]

Retrieves emails with pending status.

### Category-Based Filtering

#### get_emails_by_category(category: str, offset: int = 0) -> List[EmailDocument]

Retrieves emails filtered by category with pagination.

#### get_follow_up_emails(offset: int = 0) -> List[EmailDocument]

Retrieves follow-up emails with pagination.

#### get_quote_emails(offset: int = 0) -> List[EmailDocument]

Retrieves quote-related emails with pagination.

### Direction-Based Filtering

#### get_emails_by_direction(direction: str, offset: int = 0) -> List[EmailDocument]

Retrieves emails filtered by direction (inbound/outbound).

#### get_inbound_emails(offset: int = 0) -> List[EmailDocument]

Retrieves inbound emails with pagination.

#### get_outbound_emails(offset: int = 0) -> List[EmailDocument]

Retrieves outbound emails with pagination.

### Attachment-Based Filtering

#### get_emails_with_attachments(offset: int = 0) -> List[EmailDocument]

Retrieves emails with attachments.

#### get_processed_emails(offset: int = 0) -> List[EmailDocument]

Retrieves processed emails with pagination.

### Individual Email Retrieval

#### get_email_by_id(email_id: str) -> Optional[EmailDocument]

Retrieves a single email as a validated EmailDocument object.

## Count Methods

### Total Counts

#### count_emails() -> int

Returns total number of emails in collection.

#### count_all_emails() -> int

Alias for count_emails() for consistency.

### Filtered Counts

#### count_emails_by_status(status: str) -> int

Returns count of emails by specific status.

#### count_emails_by_category(category: str) -> int

Returns count of emails by specific category.

#### count_emails_by_direction(direction: str) -> int

Returns count of emails by direction.

#### count_emails_with_attachments() -> int

Returns count of emails with attachments.

## Statistics and Analytics

### Email Statistics

#### get_email_stats() -> Dict[str, int]

Returns comprehensive email statistics including:

- Total emails count
- Emails by status breakdown
- Emails by category
- Emails by direction
- Delivery success rates

### Performance Analytics

#### get_email_analytics() -> Dict[str, Any]

Returns email performance analytics including:

- Open rates
- Click rates
- Delivery rates
- Response rates
- Engagement metrics

## Status Management

### Status Updates

#### update_email_status(email_id: str, new_status: str) -> bool

Updates email status with automatic timestamp and validation.

#### mark_email_sent(email_id: str) -> bool

Marks email as sent with timestamp.

#### mark_email_delivered(email_id: str) -> bool

Marks email as delivered with timestamp.

#### mark_email_failed(email_id: str, reason: str) -> bool

Marks email as failed with reason tracking.

### Engagement Tracking

#### track_email_opened(email_id: str) -> bool

Records email open event with timestamp.

#### track_email_clicked(email_id: str) -> bool

Records email click event with timestamp.

### N8N Integration

#### compose_email_for_n8n(email_data: Dict[str, Any]) -> Dict[str, Any]

Composes email document for N8N automation workflow.

## Database Indexes

### Primary Indexes

- `contact_id` (ascending) - Contact-based queries
- `message_id` (ascending) - Message identification
- `thread_id` (ascending) - Thread queries
- `status` (ascending) - Status filtering
- `category` (ascending) - Category filtering
- `direction` (ascending) - Direction filtering
- `created_at` (descending) - Temporal sorting

### Compound Indexes

- `{contact_id: 1, created_at: -1}` - Contact email history
- `{status: 1, created_at: -1}` - Status with recency
- `{category: 1, direction: 1}` - Category with direction
- `{thread_id: 1, created_at: 1}` - Thread chronology

## API Endpoints

### REST Routes

All routes are prefixed with `/api/v1/mongo/emails/`

#### GET /recent?page=1

Retrieves recent emails with pagination.

#### GET /oldest?page=1

Retrieves oldest emails with pagination.

#### GET /by-status/{status}?page=1

Retrieves emails by status with pagination.

#### GET /successful?page=1

Retrieves successful emails with pagination.

#### GET /failed?page=1

Retrieves failed emails with pagination.

#### GET /pending?page=1

Retrieves pending emails with pagination.

#### GET /by-category/{category}?page=1

Retrieves emails by category with pagination.

#### GET /by-direction/{direction}?page=1

Retrieves emails by direction with pagination.

#### GET /with-attachments?page=1

Retrieves emails with attachments with pagination.

#### GET /processed?page=1

Retrieves processed emails with pagination.

#### GET /{email_id}

Retrieves a single email by ID.

#### GET /stats

Retrieves comprehensive email statistics.

## Error Handling

### Common Errors

- **EmailNotFound**: Email ID not found
- **ValidationError**: Invalid email data
- **StatusTransitionError**: Invalid status change
- **ThreadNotFound**: Thread ID not found
- **AttachmentError**: Attachment processing issues

### Error Response Format

```json
{
  "error": "EmailNotFound",
  "message": "Email with ID 'email_123' not found",
  "code": "EMAIL_NOT_FOUND"
}
```

## Usage Examples

### Creating an Email

```python
email_data = {
    "contact_id": "hubspot_12345",
    "message_id": "msg_789",
    "subject": "Quote Follow-up",
    "status": "pending",
    "direction": "outbound",
    "category": "follow_up",
    "to_email": "customer@example.com"
}
email_id = await mongo_service.create_email(email_data)
```

### Paginated Retrieval

```python
# Get page 2 of recent emails
page = 2
offset = (page - 1) * 10
emails = await mongo_service.get_recent_emails(offset=offset)

# Get total count for pagination
total = await mongo_service.count_emails()
total_pages = (total + 9) // 10
```

### Status Management

```python
# Update email status
success = await mongo_service.update_email_status(
    email_id="email_123",
    new_status="delivered"
)

# Track engagement
await mongo_service.track_email_opened(email_id="email_123")

# Get statistics
stats = await mongo_service.get_email_stats()
```

## Performance Considerations

### Optimization Tips

1. **Use indexes**: Ensure proper indexing for query patterns
2. **Limit results**: Always use pagination for large datasets
3. **Filter early**: Apply status/category filters before sorting
4. **Thread management**: Optimize thread-based queries
5. **Attachment handling**: Optimize attachment processing

### Query Patterns

- **Recent emails**: Use created_at descending index
- **Status filtering**: Use status index first
- **Category queries**: Use category index
- **Thread queries**: Use thread_id index

## Best Practices

1. **Validate data**: Use EmailDocument model for validation
2. **Track engagement**: Monitor email engagement metrics
3. **Handle failures**: Implement retry logic for failed emails
4. **Thread management**: Maintain thread integrity
5. **Performance monitoring**: Track email performance metrics

## Future Enhancements

1. **Advanced analytics**: Email performance prediction
2. **Template system**: Email template management
3. **A/B testing**: Email A/B testing framework
4. **Integration**: Enhanced automation integration
5. **Personalization**: Advanced email personalization
