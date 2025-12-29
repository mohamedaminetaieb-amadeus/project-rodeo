"""
Utility functions for processing Confluence pages and uploading to Azure Blob Storage.
"""
import io
import logging
import traceback
from typing import List, Tuple, Optional
from batch.utilities.helpers.confluence_client import ConfluenceClient, html_to_text
from batch.utilities.helpers.azure_blob_storage_client import AzureBlobStorageClient
from batch.utilities.helpers.env_helper import EnvHelper

logger = logging.getLogger(__name__)


def process_confluence_pages(
    base_url: str,
    page_ids: List[str],
    include_children: bool = False,
    auth_type: str = "basic",
    email: Optional[str] = None,
    api_token: Optional[str] = None,
    access_token: Optional[str] = None,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Process Confluence pages and upload them to Azure Blob Storage.

    Args:
        base_url: Confluence instance base URL
        page_ids: List of page IDs to process
        include_children: Whether to include child pages
        auth_type: "oauth2" or "basic"
        email: User email for basic auth
        api_token: API token for basic auth
        access_token: Access token for OAuth2 auth

    Returns:
        Tuple of (successful_uploads: List[str], errors: List[Tuple[page_id, error_message]])
    """
    successful_uploads = []
    errors = []

    try:
        # Initialize Confluence client based on auth type
        if auth_type == "oauth2":
            if not access_token:
                raise ValueError("access_token is required for OAuth2 authentication")
            confluence_client = ConfluenceClient(
                base_url=base_url,
                access_token=access_token,
                auth_type="oauth2",
            )
        else:
            if not email or not api_token:
                raise ValueError("email and api_token are required for basic authentication")
            confluence_client = ConfluenceClient(
                base_url=base_url,
                email=email,
                api_token=api_token,
                auth_type="basic",
            )

        # Verify authentication
        if not confluence_client.verify_authentication():
            raise ValueError("Failed to authenticate with Confluence")

        # Initialize blob storage client
        blob_client = AzureBlobStorageClient()

        # Collect all pages to process
        all_page_ids = []
        for page_id in page_ids:
            all_page_ids.append(page_id)
            if include_children:
                try:
                    child_pages = confluence_client.get_child_pages(page_id)
                    all_page_ids.extend([child["id"] for child in child_pages])
                except Exception as e:
                    logger.warning(
                        f"Could not fetch child pages for {page_id}: {str(e)}"
                    )

        # Process each page
        for page_id in all_page_ids:
            try:
                page_content = confluence_client.get_page_content(page_id)
                title = page_content.get("title", f"confluence-page-{page_id}")
                url = page_content.get("url", "")
                html_content = page_content.get("content", "")

                # Convert HTML to plain text
                text_content = html_to_text(html_content)

                # Prepare file content
                file_content = f"# {title}\n\nSource: {url}\n\n{text_content}"
                bytes_data = file_content.encode("utf-8")

                # Create a safe filename
                safe_filename = f"confluence_{page_id}_{title[:50]}.txt"
                safe_filename = safe_filename.replace("/", "_").replace("\\", "_")

                # Upload to blob storage
                metadata = {
                    "title": title,
                    "source": "confluence",
                    "page_id": page_id,
                    "url": url,
                }

                blob_client.upload_file(
                    bytes_data=bytes_data,
                    file_name=safe_filename,
                    content_type="text/plain",
                    metadata=metadata,
                )

                successful_uploads.append(title)
                logger.info(f"Successfully uploaded Confluence page: {title}")

            except Exception as e:
                error_msg = str(e)
                errors.append((page_id, error_msg))
                logger.error(
                    f"Error processing Confluence page {page_id}: {traceback.format_exc()}"
                )

    except Exception as e:
        logger.error(f"Error in process_confluence_pages: {traceback.format_exc()}")
        raise

    return successful_uploads, errors


def validate_confluence_credentials(
    base_url: str,
    email: Optional[str] = None,
    api_token: Optional[str] = None,
    access_token: Optional[str] = None,
    auth_type: str = "basic",
) -> Tuple[bool, str]:
    """
    Validate Confluence credentials.

    Args:
        base_url: Confluence instance base URL
        email: User email for basic auth
        api_token: API token for basic auth
        access_token: Access token for OAuth2
        auth_type: "oauth2" or "basic"

    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    try:
        if auth_type == "oauth2":
            if not access_token:
                return False, "access_token is required for OAuth2"
            confluence_client = ConfluenceClient(
                base_url=base_url,
                access_token=access_token,
                auth_type="oauth2",
            )
        else:
            if not email or not api_token:
                return False, "email and api_token are required for basic auth"
            confluence_client = ConfluenceClient(
                base_url=base_url,
                email=email,
                api_token=api_token,
                auth_type="basic",
            )

        if not confluence_client.verify_authentication():
            return False, "Failed to authenticate with provided credentials"

        spaces = confluence_client.get_spaces(limit=1)
        if not spaces:
            return False, "No spaces found or user has no access to any spaces"

        return True, "Authentication successful"
    except ValueError as e:
        return False, f"Invalid input: {str(e)}"
    except Exception as e:
        return False, f"Error validating credentials: {str(e)}"
