# Confluence Integration - Developer Setup & Testing Guide

## Prerequisites

- Python 3.10+
- Existing spec-reviewer-bot application running
- Confluence Cloud instance with test space
- Confluence API token

## Installation

The Confluence integration uses only existing dependencies (requests, streamlit). No additional packages need to be installed.

### Verify Dependencies

```bash
pip list | grep -E "requests|streamlit"
```

Both should be present in your environment.

## Environment Setup

No additional environment variables are required. The application uses:
- Existing `env_helper` for Azure configuration
- Streamlit session state for Confluence credentials (not persisted)

## File Organization

```
code/backend/
├── pages/
│   └── 01_Ingest_Data.py
├── batch/
│   ├── utilities/
│   │   └── helpers/
│   │       ├── confluence_client.py    ← NEW
│   │       └── confluence_processor.py ← NEW
│   └── ... (other batch processing files)
└── requirements.txt
```

## Running the Application

1. **Start the Streamlit app**:
```bash
cd code/backend
streamlit run ../app.py
```

2. **Navigate to "Ingest Data" page**

3. **Scroll to "Add Confluence pages to the knowledge base" section**

## Testing Guide

### Test 1: Basic Authentication

**Objective**: Verify Confluence Cloud authentication works

**Steps**:
1. Enter valid Confluence URL (e.g., `https://mycompany.atlassian.net`)
2. Enter valid email
3. Enter valid API token
4. Click "Connect to Confluence"
5. Should see: ✓ Successfully connected to Confluence!

**Expected Result**: Green success message appears

**Troubleshooting**:
- If auth fails, check credentials
- Verify API token at https://id.atlassian.com/manage-profile/security/api-tokens
- Ensure token hasn't expired

### Test 2: Space Retrieval

**Objective**: Verify spaces load correctly

**Steps**:
1. After successful auth, click space dropdown
2. Wait for spaces to load
3. Should see list of accessible spaces

**Expected Result**: Dropdown populated with space names

**Troubleshooting**:
- If no spaces appear, user may not have access
- Check Confluence permissions
- Try different Confluence instance

### Test 3: Page Selection

**Objective**: Verify pages load from selected space

**Steps**:
1. Select a space from dropdown
2. Wait for pages to load
3. Should see list of pages with titles and IDs

**Expected Result**: Pages listed in multiselect dropdown

**Troubleshooting**:
- If no pages appear, check space permissions
- Some spaces may be empty
- Check Confluence Cloud API rate limits

### Test 4: Single Page Ingestion

**Objective**: Verify single page can be ingested

**Steps**:
1. Select one page from dropdown
2. Do NOT check "Include child pages"
3. Click "Ingest 1 Page(s)"
4. Wait for processing
5. Should see success message

**Expected Result**:
- Green success message with page title
- No error messages
- Page count shows 1 ingested

**Verification**:
- Check Azure Blob Storage for new file
- Look for metadata in blob properties

### Test 5: Multiple Page Ingestion

**Objective**: Verify batch ingestion works

**Steps**:
1. Select 3-5 pages from dropdown
2. Do NOT check "Include child pages"
3. Click "Ingest X Page(s)"
4. Wait for processing

**Expected Result**:
- All pages processed successfully
- Count matches selected count
- All pages listed in success message

### Test 6: Child Pages Inclusion

**Objective**: Verify child page handling

**Steps**:
1. Find a page with child pages
2. Select the parent page
3. Check "Also include child pages of selected pages"
4. Click "Ingest X Page(s)"
5. Verify more pages were ingested than selected

**Expected Result**:
- Number of ingested pages > number of selected pages
- All parent and child pages processed

### Test 7: Error Handling

**Objective**: Verify error handling

**Steps**:
1. After successful auth, disconnect and reconnect
2. During page loading, network interruption (offline, or throttle)
3. Select page but simulate blob upload failure

**Expected Result**:
- Graceful error messages
- App doesn't crash
- User can retry

### Test 8: Invalid Credentials

**Objective**: Verify credential validation

**Steps**:
1. Enter invalid Confluence URL
2. Enter wrong email or API token
3. Click "Connect to Confluence"

**Expected Result**:
- Red error message
- Shows specific error (invalid URL, auth failed, etc.)
- User can try again

### Test 9: Metadata Verification

**Objective**: Verify metadata is stored correctly

**Steps**:
1. Ingest a page
2. Check Azure Blob Storage
3. Examine the uploaded file's metadata

**Expected Result** - Metadata should include:
```json
{
  "title": "Page Title from Confluence",
  "source": "confluence",
  "page_id": "12345678",
  "url": "https://instance.atlassian.net/wiki/spaces/KEY/pages/12345678"
}
```

### Test 10: Content Quality

**Objective**: Verify HTML to text conversion

**Steps**:
1. Ingest a page with various formatting (bold, links, lists, etc.)
2. Download the file from blob storage
3. Review the content

**Expected Result**:
- Content is readable as plain text
- All text is present
- HTML tags are removed
- Formatting is mostly preserved as text

## Debugging

### Enable Debug Logging

Set environment variable:
```bash
export LOGLEVEL=DEBUG
```

Then check logs for detailed information about:
- API calls to Confluence
- Authentication flow
- Page processing steps
- Error details

### Check Confluence API Directly

Test API connectivity independently:

```python
from batch.utilities.helpers.confluence_client import ConfluenceClient

client = ConfluenceClient(
    base_url="https://your-company.atlassian.net",
    email="your.email@company.com",
    api_token="your_api_token"
)

# Test authentication
is_valid = client.verify_authentication()
print(f"Auth valid: {is_valid}")

# Get spaces
spaces = client.get_spaces()
print(f"Spaces: {spaces}")
```

### Check Blob Upload

Verify files are being uploaded:

```python
from batch.utilities.helpers.azure_blob_storage_client import AzureBlobStorageClient

blob_client = AzureBlobStorageClient()

# List recent uploads
# (Implementation depends on your blob client methods)
```

### Monitor Streamlit Sessions

Check Streamlit logs for session state:
- Open browser dev console (F12)
- Check "Network" tab for API calls
- Monitor console for JavaScript errors

## Common Issues & Solutions

### "Connection refused" to Confluence

**Cause**: Invalid URL or network issue
**Solution**: 
- Verify URL format: `https://company.atlassian.net`
- Test connectivity: `curl https://company.atlassian.net`
- Check firewall/proxy settings

### "401 Unauthorized" response

**Cause**: Invalid email or API token
**Solution**:
- Verify email matches Confluence account
- Generate new API token
- Check token hasn't expired
- Ensure token has required permissions

### Pages don't appear in search after ingestion

**Cause**: Embeddings processing hasn't completed
**Solution**:
- Wait 5-10 minutes
- Check Azure Function logs for errors
- Verify blob upload succeeded
- Check Azure AI Search index in portal

### "429 Too Many Requests" from Confluence

**Cause**: Hit API rate limits
**Solution**:
- Wait before retrying
- Reduce batch size in future
- Space out requests
- Contact Confluence admin if limit is too low

### Memory issues with large pages

**Cause**: Very large pages consume memory
**Solution**:
- Process one page at a time
- Contact Confluence admin to split large pages
- Monitor system resources

## Performance Testing

### Test Ingestion Speed

```python
import time
from batch.utilities.helpers.confluence_processor import process_confluence_pages

start = time.time()
successful, errors = process_confluence_pages(
    base_url="...",
    email="...",
    api_token="...",
    page_ids=["id1", "id2", "id3"],
    include_children=False
)
elapsed = time.time() - start

print(f"Processed {len(successful)} pages in {elapsed:.2f} seconds")
print(f"Average: {elapsed/len(successful):.2f}s per page")
```

### Monitor API Calls

Add logging to track API performance:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("batch.utilities.helpers.confluence_client")
```

## Load Testing

For testing with many pages:

1. Create test space with 50+ pages
2. Test ingesting 10-50 pages at once
3. Monitor:
   - Blob upload speed
   - Memory usage
   - Confluence API response times
   - Streamlit session performance

## Integration with CI/CD

To add Confluence integration testing to your CI/CD:

```yaml
# Example GitHub Actions test
- name: Test Confluence Client
  run: |
    python -m pytest tests/test_confluence_client.py -v
    
- name: Lint Confluence Code
  run: |
    flake8 batch/utilities/helpers/confluence_*.py
    
- name: Type Check
  run: |
    mypy batch/utilities/helpers/confluence_*.py
```

## Support & Escalation

If issues persist:

1. **Check Documentation**:
   - See `confluence_integration.md` for architecture details
   - See `confluence_quickstart.md` for user guide

2. **Review Logs**:
   - Enable `LOGLEVEL=DEBUG`
   - Check Azure Function logs
   - Check browser console

3. **Contact**:
   - Confluence Cloud support for API issues
   - Azure support for blob/search issues
   - Application team for integration issues

## Next Steps After Testing

1. Update documentation if needed
2. Add to product release notes
3. Train users on Confluence integration
4. Monitor for issues in production
5. Plan future enhancements
