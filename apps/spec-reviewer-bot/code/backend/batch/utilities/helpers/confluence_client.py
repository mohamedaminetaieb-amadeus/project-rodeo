import requests
import base64
import logging
import traceback
from typing import Optional, List, Dict
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """
    Client for interacting with Confluence Cloud API.
    Supports OAuth2 and Basic authentication.
    """

    def __init__(
        self,
        base_url: str,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        access_token: Optional[str] = None,
        auth_type: str = "oauth2",
    ):
        """
        Initialize Confluence client.

        Args:
            base_url: Confluence instance URL (e.g., https://mycompany.atlassian.net)
            email: Email for basic auth
            api_token: API token for basic auth
            access_token: OAuth2 access token
            auth_type: "oauth2" (default) or "basic"
        """
        self.base_url = base_url.rstrip("/")
        self.auth_type = auth_type
        self.session = requests.Session()

        # Set authentication headers
        if auth_type == "oauth2" and access_token:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                }
            )
        elif auth_type == "basic" and email and api_token:
            # Basic auth for Confluence Cloud (legacy)
            credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
            self.session.headers.update(
                {
                    "Authorization": f"Basic {credentials}",
                    "Accept": "application/json",
                }
            )
        else:
            raise ValueError(
                f"Invalid auth configuration for auth_type={auth_type}: "
                f"OAuth2 requires access_token; Basic requires email and api_token"
            )

    def get_spaces(self, limit: int = 50) -> List[Dict]:
        """
        Get list of spaces the user has access to.

        Returns:
            List of space dictionaries with keys: key, name, id
        """
        try:
            url = urljoin(self.base_url, "/wiki/api/v2/spaces")
            params = {
                "limit": limit,
                "status": "current",
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            spaces = []
            for space in data.get("results", []):
                spaces.append(
                    {
                        "key": space.get("key"),
                        "name": space.get("name"),
                        "id": space.get("id"),
                    }
                )
            return spaces
        except Exception:
            logger.error(f"Error fetching spaces: {traceback.format_exc()}")
            raise

    def get_pages_in_space(self, space_key: str, limit: int = 50) -> List[Dict]:
        """
        Get pages in a specific space.

        Args:
            space_key: Space key (e.g., 'MYSPACE')
            limit: Maximum number of pages to retrieve

        Returns:
            List of page dictionaries with keys: id, title, url
        """
        try:
            url = urljoin(self.base_url, f"/wiki/api/v2/spaces/{space_key}/pages")
            params = {
                "limit": limit,
                "status": "current",
                "sort": "modified-desc",
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            pages = []
            for page in data.get("results", []):
                pages.append(
                    {
                        "id": page.get("id"),
                        "title": page.get("title"),
                        "url": page.get("_links", {}).get("webui", ""),
                    }
                )
            return pages
        except Exception:
            logger.error(
                f"Error fetching pages in space {space_key}: {traceback.format_exc()}"
            )
            raise

    def get_page_content(self, page_id: str) -> Dict:
        """
        Get the full content of a page (including children).

        Args:
            page_id: Page ID

        Returns:
            Dictionary with 'content' (HTML), 'title', and 'url'
        """
        try:
            url = urljoin(self.base_url, f"/wiki/api/v2/pages/{page_id}")
            params = {
                "body-format": "storage",  # Get HTML representation
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()

            page = response.json()
            return {
                "id": page.get("id"),
                "title": page.get("title"),
                "content": page.get("body", {}).get("storage", {}).get("value", ""),
                "url": page.get("_links", {}).get("webui", ""),
            }
        except Exception:
            logger.error(
                f"Error fetching content for page {page_id}: {traceback.format_exc()}"
            )
            raise

    def get_child_pages(self, page_id: str, limit: int = 50) -> List[Dict]:
        """
        Get child pages of a given page.

        Args:
            page_id: Parent page ID
            limit: Maximum number of child pages

        Returns:
            List of child page dictionaries
        """
        try:
            url = urljoin(
                self.base_url, f"/wiki/api/v2/pages/{page_id}/child-pages"
            )
            params = {
                "limit": limit,
                "status": "current",
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            pages = []
            for page in data.get("results", []):
                pages.append(
                    {
                        "id": page.get("id"),
                        "title": page.get("title"),
                        "url": page.get("_links", {}).get("webui", ""),
                    }
                )
            return pages
        except Exception:
            logger.error(
                f"Error fetching child pages for {page_id}: {traceback.format_exc()}"
            )
            raise

    def verify_authentication(self) -> bool:
        """
        Verify that authentication is working by fetching current user info.

        Returns:
            True if authentication is successful
        """
        try:
            url = urljoin(self.base_url, "/wiki/api/v2/me")
            response = self.session.get(url)
            return response.status_code == 200
        except Exception:
            logger.error(f"Authentication verification failed: {traceback.format_exc()}")
            return False


def html_to_text(html_content: str) -> str:
    """
    Convert HTML content to plain text for embedding.
    Removes HTML tags but preserves text content.

    Args:
        html_content: HTML string

    Returns:
        Plain text version of HTML
    """
    try:
        from html.parser import HTMLParser

        class MLStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.reset()
                self.strict = False
                self.convert_charrefs = True
                self.text = []

            def handle_data(self, data):
                self.text.append(data)

            def get_data(self):
                return " ".join(self.text)

        stripper = MLStripper()
        stripper.feed(html_content)
        return stripper.get_data()
    except Exception:
        logger.warning(
            f"Failed to parse HTML: {traceback.format_exc()}. Returning original content."
        )
        return html_content
