# Confluence Integration - Quick Start Guide

## Two Authentication Methods

### Method 1: OAuth2 (Recommended for Company-Managed Accounts)
✓ No personal API token needed
✓ Better security and compliance
✓ Automatic token refresh
✓ Requires Atlassian admin to set up (one-time)

**Setup**: See [confluence_oauth2_setup.md](confluence_oauth2_setup.md)

### Method 2: Personal API Token (Legacy)
✓ Simpler setup
✓ Works if your company allows it
✓ Requires creating personal API token

**Setup**: Continue below

---

## Using OAuth2 (Recommended)

Your admin has already configured OAuth2. Here's how to use it:

1. Open the Ingest Data page
2. Click on "Add Confluence pages to the knowledge base"
3. Enter your Confluence URL (e.g., `https://mycompany.atlassian.net`)
4. Click "Authorize with Confluence"
5. You'll be redirected to Atlassian to authorize
6. After authorization, return to the app
7. Select space → select pages → ingest

**That's it!** No tokens to manage.

---

## Using Personal API Token (If OAuth2 Not Available)

### Step 1: Get Your Confluence API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name (e.g., "Knowledge Base Ingestion")
4. Click "Create"
5. **IMPORTANT**: Copy the token now - you won't see it again

### Step 2: Find Your Confluence URL

Your Confluence URL looks like: `https://your-company.atlassian.net`

You can find it by:
- Looking at the URL when you're in Confluence
- It's the domain before `/wiki/`

### Step 3: Enter Credentials in App

1. Open Ingest Data page
2. Click "Add Confluence pages to the knowledge base"
3. Click the "Legacy (API Token)" tab
4. Fill in:
   - **Confluence URL**: `https://your-company.atlassian.net`
   - **Email**: Your Confluence account email
   - **API Token**: The token you just created
5. Click "Connect to Confluence"

---

## Steps to Ingest Confluence Pages

### Step 1: Navigate to Ingest Data Page
Open your application and click on "Ingest Data" in the navigation

### Step 2: Expand Confluence Section
Scroll down and click "Add Confluence pages to the knowledge base"

### Step 3: Authenticate
**OAuth2 Way**:
- Enter Confluence URL
- Click "Authorize with Confluence"
- Complete authorization at Atlassian
- Return to app

**API Token Way**:
- Enter Confluence URL, email, and API token
- Click "Connect to Confluence"

### Step 4: Select a Space
From the dropdown, select which Confluence space to browse

### Step 5: Choose Pages
Select one or more pages using the checkboxes

### Step 6: Optional - Include Child Pages
If you want to also ingest pages under your selected pages, check the box "Also include child pages of selected pages"

### Step 7: Ingest
Click "Ingest X Page(s)" button

### Step 8: Monitor Progress
- You'll see which pages were successfully ingested
- Any errors will be listed
- Processing is asynchronous - embeddings will be computed in the background

---

## What Happens Next?

1. Pages are downloaded from Confluence
2. HTML is converted to plain text
3. Files are uploaded to Azure Blob Storage
4. Embeddings are automatically computed
5. Content is indexed in Azure AI Search
6. Pages become searchable in your application

This typically takes a few minutes depending on page size and system load.

---

## Troubleshooting

### OAuth2 Issues

**"OAuth2 not configured" message**
- Contact your admin to set up OAuth2
- See [confluence_oauth2_setup.md](confluence_oauth2_setup.md)

**"Authorize with Confluence" doesn't work**
- Check your Confluence URL is correct
- Clear browser cookies
- Try again

**"State mismatch" error**
- Session was lost during redirect
- Clear cookies and try again

### API Token Issues

**"Authentication failed"**
- Double-check your email and API token
- Make sure you're using your Confluence Cloud instance (not Server/DC)
- Generate a new API token if the old one expired

**"No spaces found"**
- Your user account might not have access to any spaces
- Contact your Confluence administrator to grant space access

### Pages don't appear after ingestion
- Wait a few minutes - embeddings computation is asynchronous
- Check the Azure Function logs for any processing errors
- Ensure the selected space has pages (some spaces may be empty)

### "Invalid URL format"
- Make sure URL includes `https://`
- Should be like: `https://company.atlassian.net` (not `/wiki` or `/spaces`)

---

## Security Note

### OAuth2
- Your password is never shared with the app
- You authorize the app through Atlassian
- Token is stored only in your session
- Session-based - automatic logout on browser close
- Click "Disconnect from Confluence" when done

### API Token
- Token is only kept in your browser session
- Token is never stored on the server
- Click "Disconnect from Confluence" when you're done
- Each session requires fresh authentication

---

## Maximum Pages

- Currently retrieves up to 50 pages per space
- With child pages enabled, you might ingest more
- For ingesting specific pages, use the multi-select carefully

---

## Tips for Best Results

1. **Test First**: Try with 1-2 pages before large batches
2. **Clean Content**: Pages with mostly formatting might not ingest well
3. **Page Size**: Very large pages may be split during processing
4. **Child Pages**: Enable only if needed - increases processing time
5. **Timing**: Run ingestion during off-peak hours for faster processing

---

## Contact & Support

For detailed documentation, see: `confluence_integration.md`

For OAuth2 setup, see: `confluence_oauth2_setup.md`

For issues:
1. Check that your Confluence permissions are correct
2. Verify the instance URL is correct
3. Review application logs for error details
4. Contact your application administrator
