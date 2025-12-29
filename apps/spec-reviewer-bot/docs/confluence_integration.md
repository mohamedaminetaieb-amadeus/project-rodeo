# Confluence Integration for Document Ingestion

## Overview

This document describes the Confluence integration feature that allows users to authenticate with their Confluence Cloud instance and select pages for ingestion into the vector knowledge base.

The integration supports both **OAuth2** (recommended) and **legacy API token** authentication methods.

## Features

- **OAuth2 Authentication** (Recommended): Secure, company-managed accounts supported, no personal tokens
- **API Token Authentication** (Legacy): Fallback option for simpler setups
- **Space Navigation**: Browse and select from available Confluence spaces
- **Page Selection**: Multi-select pages from the chosen space
- **Child Pages**: Optional inclusion of child pages in ingestion
- **Metadata Preservation**: Confluence page metadata (title, URL, page ID) is stored with ingested documents
- **HTML to Text Conversion**: Confluence pages (stored as HTML) are converted to plain text for embedding
- **Automatic Token Refresh**: OAuth2 tokens are automatically refreshed without user intervention

## Authentication Methods

### OAuth2 (Recommended)

**Best for**: Company-managed Confluence accounts, enterprise environments

**How it works**:
1. User clicks "Authorize with Confluence"
2. Redirected to Atlassian authentication service
3. User logs in and grants permissions
4. Authorization code is exchanged for access token
5. Token stored securely in session
6. Automatic refresh when token expires

**Advantages**:
- No personal API tokens needed
- Better security model
- Transparent audit trail
- Automatic token refresh
- Complies with company policies

**Setup**: See [confluence_oauth2_setup.md](confluence_oauth2_setup.md)

### API Token (Legacy)

**Best for**: Personal use, simplified setups where OAuth2 not available

**How it works**:
1. User generates API token from Atlassian profile
2. Enters email and token in application
3. Application authenticates using Basic Auth
4. Token stored only in session

**Advantages**:
- Simpler setup
- No Atlassian admin required
- Works in any environment

**Disadvantages**:
- Uses personal API token
- Company may restrict token creation
- No automatic refresh
- Less secure than OAuth2

## How to Use

### Using OAuth2 (Recommended)

1. **Prerequisite**: Admin has configured OAuth2 in Atlassian app console
2. Open the Streamlit app and go to "Ingest Data" page
3. Expand "Add Confluence pages to the knowledge base"
4. Enter your Confluence instance URL
5. Click "Authorize with Confluence"
6. You'll be redirected to Atlassian
7. Review permissions and click "Allow"
8. You'll return to the application
9. Select space, pages, and ingest

### Using API Token (Fallback)

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create a new API token
3. Open the Streamlit app and go to "Ingest Data" page
4. Click "Legacy (API Token)" tab
5. Enter: Confluence URL, email, API token
6. Click "Connect to Confluence"
7. Select space, pages, and ingest

## Architecture

### Components

#### 1. `confluence_client.py`
Handles all interactions with Confluence Cloud API:
- `ConfluenceClient` class: API v2 client with support for both auth methods
- Supports both OAuth2 access tokens and basic authentication
- Methods:
  - `get_spaces()`: Retrieve list of accessible spaces
  - `get_pages_in_space()`: Get pages in a specific space
  - `get_page_content()`: Fetch full page content with HTML
  - `get_child_pages()`: Retrieve child pages
  - `verify_authentication()`: Test authentication status (works with both methods)
- `html_to_text()`: Convert HTML content to plain text

#### 2. `confluence_oauth.py` (NEW)
OAuth2 authentication handler:
- `ConfluenceOAuth2` class: Implements authorization code flow
  - `get_authorization_url()`: Generate authorization URL
  - `exchange_code_for_token()`: Exchange auth code for access token
  - `refresh_access_token()`: Refresh expired access token
  - `is_token_expired()`: Check token expiration
  - `get_user_info()`: Fetch user information
- `TokenManager` class: In-memory token storage with refresh logic
- `extract_cloud_id_from_response()`: Parse cloud ID from token response

#### 3. `confluence_processor.py`
Processes Confluence pages and uploads to Azure:
- `process_confluence_pages()`: Main function to ingest multiple pages
  - Supports both OAuth2 and API token authentication
  - Authenticates with Confluence
  - Retrieves page content
  - Converts HTML to text
  - Uploads to Azure Blob Storage with metadata
  - Handles errors gracefully
- `validate_confluence_credentials()`: Test credentials before full processing (supports both auth types)

#### 4. `01_Ingest_Data.py` (Modified)
Streamlit UI for Confluence integration:
- `handle_confluence_auth()`: Main authentication handler that chooses OAuth2 or legacy
- `handle_oauth2_auth()`: OAuth2-specific authentication flow
- `handle_legacy_auth()`: Legacy API token authentication form
- `display_confluence_page_selector()`: Space and page selection UI (works with both auth types)
- New expander section for Confluence ingestion with tabbed interface

### Data Flow (OAuth2)

```
User Credentials
    ↓
Confluence URL Input
    ↓
handle_oauth2_auth()
    ↓
get_authorization_url()
    ↓
Redirect to Atlassian Auth
    ↓
User Logs In & Authorizes
    ↓
Redirect to App with Code
    ↓
exchange_code_for_token()
    ↓
Access Token Obtained
    ↓
ConfluenceClient (with Bearer token)
    ↓
Confluence Cloud API
    ↓
Page Content (HTML)
    ↓
html_to_text() conversion
    ↓
confluence_processor.process_confluence_pages()
    ↓
AzureBlobStorageClient.upload_file()
    ↓
Azure Blob Storage
    ↓
Batch Processing (Embeddings)
    ↓
Azure AI Search Index
```

### Data Flow (API Token - Legacy)

```
User Credentials
    ↓
handle_legacy_auth()
    ↓
Email + API Token Input
    ↓
ConfluenceClient (with Basic Auth)
    ↓
Confluence Cloud API
    ↓
(Rest same as OAuth2)
```

## Configuration

### OAuth2 Configuration

Requires one-time setup by Atlassian admin. See [confluence_oauth2_setup.md](confluence_oauth2_setup.md).

Required environment variables/secrets:
```
CONFLUENCE_OAUTH_CLIENT_ID = "your-client-id"
CONFLUENCE_OAUTH_CLIENT_SECRET = "your-client-secret"
CONFLUENCE_OAUTH_REDIRECT_URI = "http://localhost:8501/auth/callback"
```

### Confluence Cloud API Endpoints

- **Base URL**: `https://{instance}.atlassian.net/wiki/api/v2`
- `/spaces`: List accessible spaces
- `/spaces/{key}/pages`: Get pages in a space
- `/pages/{id}`: Get page content
- `/pages/{id}/child-pages`: Get child pages

### API Authentication

**OAuth2**: Uses Bearer token in Authorization header
```
Authorization: Bearer {access_token}
```

**API Token**: Uses Basic authentication
```
Authorization: Basic {base64(email:token)}
```

## Error Handling

The implementation includes comprehensive error handling:

1. **Authentication Errors**: Invalid credentials are caught and reported
2. **Network Errors**: Connection issues to Confluence API are handled
3. **Permission Errors**: Users see appropriate messages for access restrictions
4. **Content Processing Errors**: Individual page errors don't stop the batch process
5. **Blob Storage Errors**: Upload failures are tracked and reported
6. **Token Expiration**: OAuth2 tokens are automatically refreshed
7. **Redirect Errors**: OAuth2 callback validation prevents token theft

## Metadata Storage

Each ingested Confluence page includes the following metadata:

```python
{
    "title": "Page Title",
    "source": "confluence",
    "page_id": "12345678",
    "url": "https://instance.atlassian.net/wiki/spaces/KEY/pages/12345678"
}
```

This metadata can be used for:
- Filtering search results by source
- Tracking document lineage
- Creating links back to original Confluence pages
- Analytics and usage tracking

## Security Considerations

### OAuth2 Security

1. **Authorization Code Flow**: Secure token exchange
2. **No Credentials Exposed**: User password never sent to app
3. **State Parameter**: Prevents CSRF attacks on callback
4. **HTTPS Required**: All API calls use HTTPS
5. **Token Storage**: Only in session memory (not persistent)
6. **Token Expiration**: Automatic refresh with refresh tokens
7. **Audit Trail**: All OAuth operations logged in Atlassian

### API Token Security

1. **Token Entropy**: API tokens have sufficient entropy
2. **Basic Auth**: HTTPS only (enforced by Streamlit)
3. **Session Storage**: Not persisted to disk
4. **User Controlled**: User explicitly pastes token
5. **No Credentials in Logs**: Sensitive data excluded from logging

### General Security

1. **Input Validation**: All user inputs validated
2. **Error Messages**: Generic messages to users, detailed logs for admins
3. **HTTPS Only**: All API calls use HTTPS
4. **No Credentials in Logs**: Sensitive data excluded from logging

## Limitations

1. **Confluence Cloud Only**: Currently supports Confluence Cloud; Server/DC requires different auth
2. **API Rate Limiting**: Subject to Confluence Cloud API rate limits
3. **Page Size**: Large pages may be split during embedding (2MB max per item)
4. **Nested Pages**: Only direct child pages are retrieved (not deep recursion)
5. **Attachments**: Page attachments are not automatically included

## Future Enhancements

Potential improvements to consider:

1. **Multiple Confluence Instances**: Support for different instances per user
2. **Page Caching**: Cache space/page listings to reduce API calls
3. **Incremental Updates**: Track page versions and only update changed content
4. **Attachment Support**: Include page attachments in knowledge base
5. **Search API**: Confluence search integration for finding pages
6. **Page Preview**: Show page previews before ingestion
7. **Scheduled Syncing**: Periodically sync Confluence pages
8. **Confluence Server Support**: Add support for self-hosted Confluence
9. **Token Revocation**: Interface to revoke OAuth2 access

## Troubleshooting

### Common OAuth2 Issues

**Issue**: "OAuth2 not configured" message
- **Cause**: Environment variables not set
- **Solution**: Check CONFLUENCE_OAUTH_CLIENT_ID and CONFLUENCE_OAUTH_CLIENT_SECRET are configured

**Issue**: "Authorize with Confluence" doesn't work
- **Cause**: Redirect URI mismatch
- **Solution**: Verify redirect URI matches exactly in Atlassian app settings

**Issue**: "State mismatch" error
- **Cause**: Session cookie lost during redirect
- **Solution**: Clear cookies and try again

**Issue**: Token not refreshing
- **Cause**: Refresh token expired
- **Solution**: Re-authorize from scratch

### Common API Token Issues

**Issue**: Authentication fails with invalid credentials
- **Solution**: Verify email and API token are correct; generate new token if needed

**Issue**: No spaces appear after authentication
- **Solution**: User may not have access to any spaces; check Confluence permissions

**Issue**: Pages fail to ingest with "Permission Denied"
- **Solution**: Check that user has view permissions for selected pages

### Logging

Enable detailed logging by setting environment variable:
```
LOGLEVEL=DEBUG
```

Logs will show:
- OAuth flow steps and decisions
- API request/response details
- Authentication decisions
- Token management operations
- Page processing progress
- Error stack traces

## Related Files

- `/code/backend/batch/utilities/helpers/confluence_client.py`: Confluence API client
- `/code/backend/batch/utilities/helpers/confluence_oauth.py`: OAuth2 handler
- `/code/backend/batch/utilities/helpers/confluence_processor.py`: Page processing logic
- `/code/backend/pages/01_Ingest_Data.py`: Streamlit UI
- `/docs/confluence_oauth2_setup.md`: OAuth2 setup guide
- `/docs/confluence_quickstart.md`: User quick start
- `/code/backend/requirements.txt`: Python dependencies

## Support

For issues or questions:

1. **OAuth2 setup**: See [confluence_oauth2_setup.md](confluence_oauth2_setup.md)
2. **User guide**: See [confluence_quickstart.md](confluence_quickstart.md)
3. **Developer setup**: See [confluence_setup_testing.md](confluence_setup_testing.md)
4. **Confluence Cloud API**: https://developer.atlassian.com/cloud/confluence/rest/v2/
5. **OAuth2 docs**: https://developer.atlassian.com/cloud/confluence/oauth-2-authorization-code-grants-3lo-3lo/

## How to Use

### 1. Prerequisites

Users need:
- Confluence Cloud account with access to at least one space
- Confluence API token (can be generated at https://id.atlassian.com/manage-profile/security/api-tokens)
- Confluence instance URL (e.g., `https://your-company.atlassian.net`)

### 2. Steps to Ingest Confluence Pages

1. **Open the Streamlit App**: Navigate to the "Ingest Data" page
2. **Expand Confluence Section**: Click on "Add Confluence pages to the knowledge base"
3. **Enter Credentials**:
   - Confluence Instance URL
   - Email Address
   - API Token
4. **Connect**: Click "Connect to Confluence"
5. **Select Space**: Choose a space from the dropdown
6. **Select Pages**: Use the multiselect box to choose one or more pages
7. **Include Children** (Optional): Check the box to also ingest child pages
8. **Ingest**: Click "Ingest X Page(s)" to start the process
9. **Monitor**: The app will show success/error messages for each page

## Architecture

### Components

#### 1. `confluence_client.py`
Handles all interactions with Confluence Cloud API:
- `ConfluenceClient` class: Main client for API calls
- Methods:
  - `get_spaces()`: Retrieve list of accessible spaces
  - `get_pages_in_space()`: Get pages in a specific space
  - `get_page_content()`: Fetch full page content with HTML
  - `get_child_pages()`: Retrieve child pages
  - `verify_authentication()`: Test authentication status
- `html_to_text()`: Convert HTML content to plain text

#### 2. `confluence_processor.py`
Processes Confluence pages and uploads to Azure:
- `process_confluence_pages()`: Main function to ingest multiple pages
  - Authenticates with Confluence
  - Retrieves page content
  - Converts HTML to text
  - Uploads to Azure Blob Storage with metadata
  - Handles errors gracefully
- `validate_confluence_credentials()`: Test credentials before full processing

#### 3. `01_Ingest_Data.py` (Modified)
Streamlit UI for Confluence integration:
- `handle_confluence_auth()`: Authentication form and validation
- `display_confluence_page_selector()`: Space and page selection UI
- New expander section for Confluence ingestion

### Data Flow

```
User Credentials
    ↓
ConfluenceClient (API calls)
    ↓
Confluence Cloud API
    ↓
Page Content (HTML)
    ↓
html_to_text() conversion
    ↓
confluence_processor.process_confluence_pages()
    ↓
AzureBlobStorageClient.upload_file()
    ↓
Azure Blob Storage
    ↓
Batch Processing (Embeddings)
    ↓
Azure AI Search Index
```

## Configuration

### Confluence Cloud API Authentication

The integration uses **API Token Authentication** with Confluence Cloud:

1. Users generate an API token at: https://id.atlassian.com/manage-profile/security/api-tokens
2. Token is passed with email to create Basic Auth header
3. Credentials are stored in Streamlit session state (not persisted)

### API Endpoints Used

- **Base URL**: `https://{instance}.atlassian.net/wiki/api/v2`
- `/spaces`: List accessible spaces
- `/spaces/{key}/pages`: Get pages in a space
- `/pages/{id}`: Get page content
- `/pages/{id}/child-pages`: Get child pages

## Error Handling

The implementation includes comprehensive error handling:

1. **Authentication Errors**: Invalid credentials are caught and reported
2. **Network Errors**: Connection issues to Confluence API are handled
3. **Permission Errors**: Users see appropriate messages for access restrictions
4. **Content Processing Errors**: Individual page errors don't stop the batch process
5. **Blob Storage Errors**: Upload failures are tracked and reported

## Metadata Storage

Each ingested Confluence page includes the following metadata:

```python
{
    "title": "Page Title",
    "source": "confluence",
    "page_id": "12345678",
    "url": "https://instance.atlassian.net/wiki/spaces/KEY/pages/12345678"
}
```

This metadata can be used for:
- Filtering search results by source
- Tracking document lineage
- Creating links back to original Confluence pages
- Analytics and usage tracking

## Security Considerations

1. **API Tokens**: Never stored persistently; only in session memory
2. **User Input**: All user inputs are validated before API calls
3. **Error Messages**: Detailed errors logged but generic messages shown to users
4. **HTTPS Only**: All API calls use HTTPS
5. **No Credentials in Logs**: Sensitive data excluded from logging

## Limitations

1. **Confluence Cloud Only**: Currently supports Confluence Cloud; Server/DC would require different authentication
2. **API Rate Limiting**: Subject to Confluence Cloud API rate limits
3. **Page Size**: Large pages may be split during embedding
4. **Nested Pages**: Only direct child pages are retrieved (not deep recursion)
5. **Attachments**: Page attachments are not automatically included

## Future Enhancements

Potential improvements to consider:

1. **OAuth2 Flow**: Replace API token with OAuth2 for better security
2. **Page Caching**: Cache space/page listings to reduce API calls
3. **Incremental Updates**: Track page versions and only update changed content
4. **Attachment Support**: Include page attachments in knowledge base
5. **Search API**: Confluence search integration for finding pages
6. **Page Preview**: Show page previews before ingestion
7. **Scheduled Syncing**: Periodically sync Confluence pages
8. **Confluence Server Support**: Add support for self-hosted Confluence

## Troubleshooting

### Common Issues

**Issue**: Authentication fails with invalid credentials
- **Solution**: Verify email and API token are correct; generate new token if needed

**Issue**: No spaces appear after authentication
- **Solution**: User may not have access to any spaces; check Confluence permissions

**Issue**: Pages fail to ingest with "Permission Denied"
- **Solution**: Check that user has view permissions for selected pages

**Issue**: HTML to text conversion produces garbled output
- **Solution**: Some special formatting may not convert perfectly; this is expected

### Logging

Enable detailed logging by setting environment variable:
```
LOGLEVEL=DEBUG
```

Logs will show:
- API request/response details
- Authentication flow
- Page processing progress
- Error stack traces

## Testing

To test the Confluence integration:

1. Create test Confluence space with sample pages
2. Create test API token
3. Test authentication with invalid credentials (should fail gracefully)
4. Test with valid credentials and single page
5. Test with multiple pages
6. Test with child pages enabled
7. Verify metadata in uploaded files
8. Check embeddings are created in Azure AI Search

## Related Files

- `/code/backend/batch/utilities/helpers/confluence_client.py`: Confluence API client
- `/code/backend/batch/utilities/helpers/confluence_processor.py`: Page processing logic
- `/code/backend/pages/01_Ingest_Data.py`: Streamlit UI
- `/code/backend/requirements.txt`: Python dependencies

## Support

For issues or questions about the Confluence integration:

1. Check the troubleshooting section above
2. Review detailed logs with `LOGLEVEL=DEBUG`
3. Verify Confluence API token has required permissions
4. Check Confluence Cloud API documentation: https://developer.atlassian.com/cloud/confluence/rest/v2/
