# Confluence OAuth2 Setup Guide

## Overview

This guide explains how to set up OAuth2 authentication for Confluence Cloud integration. OAuth2 is the recommended authentication method for company-managed Confluence accounts where personal API tokens are not allowed.

## Why OAuth2?

✓ **Company-Managed Compliance** - No personal API tokens needed
✓ **Better Security** - Tokens don't contain user credentials
✓ **Transparent Auditing** - Each integration is registered and tracked
✓ **User Control** - Users authorize the application explicitly
✓ **Token Expiration** - Automatic token refresh without re-authentication

## Prerequisites

- Access to Atlassian Administration Console (usually requires admin access)
- Company-managed Confluence Cloud instance
- The application deployed with a static redirect URI

## Step 1: Create an OAuth2 Application in Atlassian

1. Go to https://developer.atlassian.com/console/apps
2. Click **Create app**
3. Select **OAuth 2.0 (3LO)** - This is for company-managed accounts
4. Fill in the app details:
   - **App name**: e.g., "Knowledge Base Ingestion"
   - **App description**: e.g., "Confluence page ingestion for knowledge base"
   - **Company name**: Your company name
5. Click **Create**

## Step 2: Configure Authorization Settings

1. In the app settings, go to **Authorization** section
2. Click **Add** next to "Redirect URL"
3. Enter your application's redirect URI:
   ```
   http://localhost:8501/auth/callback
   ```
   
   **For Production**, use your actual domain:
   ```
   https://your-app-domain.com/auth/callback
   https://your-app-domain.com/pages/auth/callback
   ```

4. Save the authorization settings

## Step 3: Request Scopes

1. Go to **Permissions** tab
2. Under "Scopes", add these scopes:
   - ✓ `read:confluence-content.all` - Read all Confluence content
   - ✓ `search:confluence` - Search Confluence
   - ✓ `offline_access` - Get refresh tokens for long-lived access
3. Save scopes

## Step 4: Get Client Credentials

1. Go to **Settings** tab
2. You'll see:
   - **Client ID**: Copy this
   - **Client secret**: Copy this (keep this secure!)
3. These are your OAuth2 credentials

## Step 5: Configure the Application

Add the following to your Streamlit secrets (`~/.streamlit/secrets.toml` or via Streamlit Cloud):

```toml
CONFLUENCE_OAUTH_CLIENT_ID = "your-client-id-here"
CONFLUENCE_OAUTH_CLIENT_SECRET = "your-client-secret-here"
CONFLUENCE_OAUTH_REDIRECT_URI = "http://localhost:8501/auth/callback"
```

For production, update the redirect URI to match your actual application URL.

### Using Environment Variables Instead

Alternatively, set environment variables:
```bash
export CONFLUENCE_OAUTH_CLIENT_ID="your-client-id"
export CONFLUENCE_OAUTH_CLIENT_SECRET="your-client-secret"
export CONFLUENCE_OAUTH_REDIRECT_URI="https://your-domain.com/auth/callback"
```

## Step 6: Test the Integration

1. Start the Streamlit application
2. Navigate to "Ingest Data" page
3. Expand "Add Confluence pages to the knowledge base"
4. You should see "OAuth2" as the default authentication option
5. Enter your Confluence instance URL
6. Click "Authorize with Confluence"
7. You'll be redirected to Atlassian to authorize the app
8. After authorization, you'll be redirected back to the application
9. You should see your Confluence spaces and pages

## OAuth2 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User Interface                                                  │
├─────────────────────────────────────────────────────────────────┤
│ 1. User enters Confluence URL                                  │
│ 2. Clicks "Authorize with Confluence"                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ Application Backend                                             │
├─────────────────────────────────────────────────────────────────┤
│ 3. Generates authorization URL                                 │
│ 4. User redirected to Atlassian auth service                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ Atlassian Authentication Service                                │
├─────────────────────────────────────────────────────────────────┤
│ 5. User logs in (if needed)                                    │
│ 6. User reviews permissions                                    │
│ 7. User clicks "Authorize"                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ Application Backend (Callback)                                  │
├─────────────────────────────────────────────────────────────────┤
│ 8. Receives authorization code                                 │
│ 9. Exchanges code for access token                             │
│ 10. Stores token in session                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ Confluence Cloud API                                            │
├─────────────────────────────────────────────────────────────────┤
│ 11. User can now access Confluence API                         │
│ 12. Spaces and pages are retrieved                             │
│ 13. Pages are ingested as usual                                │
└─────────────────────────────────────────────────────────────────┘
```

## Token Refresh

The OAuth2 implementation automatically handles token refresh:

- **Access Token**: Valid for ~1 hour
- **Refresh Token**: Valid for 90 days (company-managed accounts)
- **Automatic Refresh**: When token expires, the application uses the refresh token to get a new one
- **No User Action Required**: Users don't need to re-authenticate

## Fallback to Legacy Authentication

If OAuth2 is not configured, the application automatically falls back to legacy API token authentication:

1. OAuth2 section will show: "ℹ️ Using OAuth2 authentication"
2. If OAuth2 not configured, you'll see: "⚠️ OAuth2 not configured. Using legacy API token"
3. You can switch between OAuth2 and legacy in tabs

To use legacy API token auth:
1. Still go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Generate a new API token
3. Use email + token in the legacy tab

## Security Best Practices

✓ **Never commit secrets** - Use environment variables or Streamlit secrets
✓ **HTTPS Only** - In production, always use HTTPS for redirect URI
✓ **Secrets Management** - Store client secret securely (never in code)
✓ **Token Scope** - Only request necessary scopes
✓ **Token Expiration** - Regularly refresh tokens
✓ **Audit Logs** - Monitor OAuth token usage in Atlassian admin panel

## Troubleshooting

### "OAuth2 not configured" message
**Cause**: Environment variables or secrets not set
**Solution**: 
1. Check `CONFLUENCE_OAUTH_CLIENT_ID` and `CONFLUENCE_OAUTH_CLIENT_SECRET` are set
2. Restart the application
3. Check logs for errors

### "State mismatch" error during callback
**Cause**: Session was lost or modified during redirect
**Solution**:
1. Clear browser cookies
2. Try authorization again
3. Check redirect URI matches exactly

### "Redirect URI mismatch" from Atlassian
**Cause**: Redirect URI in app settings doesn't match application
**Solution**:
1. Check exact URL including protocol and port
2. Update in Atlassian app settings
3. For localhost: ensure port 8501 is correct
4. For production: ensure full domain is used

### "Insufficient permissions" error
**Cause**: Application doesn't have required scopes
**Solution**:
1. Check scopes in Atlassian app settings
2. Ensure these are added:
   - `read:confluence-content.all`
   - `search:confluence`
   - `offline_access`
3. User may need to re-authorize after scope changes

### Token not refreshing automatically
**Cause**: Refresh token expired or corrupted
**Solution**:
1. Clear application cache/session
2. Re-authorize from scratch
3. Check that `offline_access` scope is requested

## Monitoring and Auditing

### Check Token Usage in Atlassian Admin

1. Go to your Confluence instance admin panel
2. Navigate to **Security > OAuth consents**
3. You'll see all authorized OAuth applications
4. Review when tokens were last used
5. Revoke access if needed

### Logging

Enable debug logging to see OAuth flow details:

```bash
export LOGLEVEL=DEBUG
```

This will show:
- Authorization URL generation
- Code exchange process
- Token refresh operations
- API calls with auth headers

## Migration from API Tokens

If you're currently using API tokens and want to switch to OAuth2:

1. **Set up OAuth2** - Follow this guide
2. **Test OAuth2** - Verify it works in development
3. **Deploy** - Update application configuration
4. **Migrate Users** - Instruct users to authorize via OAuth2
5. **Disable API tokens** - Once all users migrated, remove token-based auth

## API Token Alternative

If your company still allows personal API tokens:

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name: "Knowledge Base Ingestion"
4. Copy the token
5. Use the "Legacy (API Token)" tab in the application
6. Enter email and token

## Support

For OAuth2 setup issues:

1. **Atlassian Documentation**: https://developer.atlassian.com/cloud/confluence/oauth-2-authorization-code-grants-3lo-3lo/
2. **Check logs** with `LOGLEVEL=DEBUG`
3. **Verify credentials** in Atlassian console
4. **Check redirect URI** matches exactly
5. **Contact your Atlassian admin** for permission issues

## Advanced Configuration

### Custom Redirect Handling

For advanced deployments, you can customize the redirect URI handling. See the Streamlit documentation for server configuration options.

### Token Storage

By default, tokens are stored in Streamlit session state (memory). For production deployments with multiple containers, consider implementing persistent token storage using:
- Database
- Redis
- File system (with proper security)

Update `confluence_oauth.py` `TokenManager` class to implement custom storage.

### Multiple Confluence Instances

To support multiple Confluence instances with OAuth2:

1. Create separate OAuth apps in each Confluence instance
2. Store client credentials per instance
3. Modify the UI to accept instance selection
4. Maintain separate token managers per instance

---

**Status**: Ready for deployment
**OAuth2 Support**: Full
**Fallback Support**: Legacy API tokens
**Token Refresh**: Automatic
