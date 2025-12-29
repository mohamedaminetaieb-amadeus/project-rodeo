from os import path
import re
import streamlit as st
import traceback
import requests
import urllib.parse
import sys
import logging
from batch.utilities.helpers.config.config_helper import ConfigHelper
from batch.utilities.helpers.env_helper import EnvHelper
from batch.utilities.helpers.azure_blob_storage_client import AzureBlobStorageClient
from batch.utilities.helpers.confluence_client import ConfluenceClient
from batch.utilities.helpers.confluence_processor import (
    process_confluence_pages,
    validate_confluence_credentials,
)
from batch.utilities.helpers.confluence_oauth import (
    ConfluenceOAuth2,
    TokenManager,
    extract_cloud_id_from_response,
)

sys.path.append(path.join(path.dirname(__file__), ".."))
env_helper: EnvHelper = EnvHelper()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Ingest Data",
    page_icon=path.join("images", "favicon.ico"),
    layout="wide",
    menu_items=None,
)


def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Load the common CSS
load_css("pages/common.css")


def reprocess_all():
    backend_url = urllib.parse.urljoin(
        env_helper.BACKEND_URL, "/api/BatchStartProcessing"
    )
    params = {}
    if env_helper.FUNCTION_KEY is not None:
        params["code"] = env_helper.FUNCTION_KEY
        params["clientId"] = "clientKey"

    try:
        response = requests.post(backend_url, params=params)
        if response.status_code == 200:
            st.success(
                f"{response.text}\nPlease note this is an asynchronous process and may take a few minutes to complete."
            )
        else:
            st.error(f"Error: {response.text}")
    except Exception:
        logger.error(traceback.format_exc())
        st.error(traceback.format_exc())


def add_urls():
    urls = st.session_state["urls"].split("\n")
    result = add_url_embeddings(urls)
    # If URLs are valid and processed, clear the textarea
    if result:
        st.session_state["urls"] = ""


def sanitize_metadata_value(value):
    # Remove invalid characters
    return re.sub(r"[^a-zA-Z0-9-_ .]", "?", value)


def add_url_embeddings(urls: list[str]):
    has_valid_url = bool(list(filter(str.strip, urls)))
    if not has_valid_url:
        st.error("Please enter at least one valid URL.")
        return False

    params = {}
    if env_helper.FUNCTION_KEY is not None:
        params["code"] = env_helper.FUNCTION_KEY
        params["clientId"] = "clientKey"
    for url in urls:
        body = {"url": url}
        backend_url = urllib.parse.urljoin(
            env_helper.BACKEND_URL, "/api/AddURLEmbeddings"
        )
        r = requests.post(url=backend_url, params=params, json=body)
        if not r.ok:
            st.error(f"Error {r.status_code}: {r.text}")
            return False
        else:
            st.success(f"Embeddings added successfully for {url}")
    return True


def handle_confluence_auth():
    """Handle Confluence authentication (OAuth2 or legacy API token)."""
    # Get OAuth2 config from environment or config
    oauth_client_id = st.secrets.get("CONFLUENCE_OAUTH_CLIENT_ID", None)
    oauth_client_secret = st.secrets.get("CONFLUENCE_OAUTH_CLIENT_SECRET", None)
    oauth_redirect_uri = st.secrets.get("CONFLUENCE_OAUTH_REDIRECT_URI", "http://localhost:8501/auth/callback")

    # Determine if OAuth2 is available
    use_oauth = oauth_client_id and oauth_client_secret

    st.subheader("Confluence Authentication")
    
    if use_oauth:
        st.info(
            "ℹ️ Using OAuth2 authentication (Company-managed accounts supported)"
        )
    else:
        st.warning(
            "⚠️ OAuth2 not configured. Using legacy API token authentication. "
            "Set CONFLUENCE_OAUTH_CLIENT_ID and CONFLUENCE_OAUTH_CLIENT_SECRET in secrets to enable OAuth2."
        )

    # Tabs for different auth methods
    if use_oauth:
        auth_tab1, auth_tab2 = st.tabs(["OAuth2", "Legacy (API Token)"])
        
        with auth_tab1:
            handle_oauth2_auth(oauth_client_id, oauth_client_secret, oauth_redirect_uri)
        
        with auth_tab2:
            handle_legacy_auth()
    else:
        handle_legacy_auth()

    if st.session_state.get("confluence_authenticated"):
        return True
    return False


def handle_oauth2_auth(client_id: str, client_secret: str, redirect_uri: str):
    """Handle OAuth2 authentication flow."""
    
    # Initialize OAuth2 handler
    oauth = ConfluenceOAuth2(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    # Check if we're in the callback phase
    query_params = st.query_params
    if "code" in query_params:
        # Handle OAuth callback
        auth_code = query_params["code"]
        state = query_params.get("state", "")

        if state != st.session_state.get("oauth_state"):
            st.error("✗ State mismatch - OAuth callback validation failed")
            return

        with st.spinner("Completing OAuth2 authentication..."):
            try:
                token_data = oauth.exchange_code_for_token(auth_code)
                st.session_state["confluence_token_data"] = token_data
                st.session_state["confluence_auth_type"] = "oauth2"
                st.session_state["confluence_oauth_client"] = oauth
                st.session_state["confluence_authenticated"] = True

                # Extract Confluence URL from token response if available
                if "confluence_url" not in st.session_state:
                    # User will need to provide this or it should come from config
                    st.session_state["confluence_url"] = None

                st.success("✓ OAuth2 authentication successful!")
                st.rerun()
            except Exception as e:
                st.error(f"✗ OAuth2 authentication failed: {str(e)}")

    else:
        # Show authorization button
        col1, col2 = st.columns(2)
        
        with col1:
            confluence_url = st.text_input(
                "Confluence Instance URL",
                placeholder="https://your-company.atlassian.net",
                value=st.session_state.get("confluence_url", ""),
                help="Required to connect to your Confluence instance",
            )

        if confluence_url:
            if st.button("Authorize with Confluence", key="oauth_authorize"):
                # Generate authorization URL
                auth_url, state = oauth.get_authorization_url()
                st.session_state["oauth_state"] = state
                st.session_state["confluence_url"] = confluence_url

                st.info(
                    f"Please click the link below to authorize:\n\n[Authorize with Confluence]({auth_url})"
                )
                st.markdown(
                    "After authorization, you'll be redirected back to this page."
                )


def handle_legacy_auth():
    """Handle legacy API token authentication."""
    with st.form("confluence_legacy_auth_form"):
        col1, col2 = st.columns(2)
        with col1:
            confluence_url = st.text_input(
                "Confluence Instance URL",
                placeholder="https://your-company.atlassian.net",
                value=st.session_state.get("confluence_url", ""),
            )
        with col2:
            confluence_email = st.text_input(
                "Email Address",
                placeholder="your.email@company.com",
                value=st.session_state.get("confluence_email", ""),
            )

        confluence_token = st.text_input(
            "API Token",
            type="password",
            placeholder="Your Confluence API token",
            help="Generate at https://id.atlassian.com/manage-profile/security/api-tokens",
        )

        submit_auth = st.form_submit_button("Connect to Confluence")

    if submit_auth:
        if not confluence_url or not confluence_email or not confluence_token:
            st.error("Please fill in all authentication fields")
            return

        with st.spinner("Validating credentials..."):
            is_valid, message = validate_confluence_credentials(
                confluence_url, confluence_email, confluence_token, auth_type="basic"
            )

        if is_valid:
            st.session_state["confluence_url"] = confluence_url
            st.session_state["confluence_email"] = confluence_email
            st.session_state["confluence_token"] = confluence_token
            st.session_state["confluence_auth_type"] = "basic"
            st.session_state["confluence_authenticated"] = True
            st.success("✓ Successfully connected to Confluence!")
            st.rerun()
        else:
            st.error(f"✗ Authentication failed: {message}")


def display_confluence_page_selector():
    """Display space and page selector for authenticated users."""
    try:
        auth_type = st.session_state.get("confluence_auth_type", "basic")
        
        # Get Confluence client based on auth type
        if auth_type == "oauth2":
            token_data = st.session_state.get("confluence_token_data", {})
            access_token = token_data.get("access_token")
            if not access_token:
                st.error("✗ OAuth2 token not found. Please re-authenticate.")
                return
            
            confluence_client = ConfluenceClient(
                base_url=st.session_state["confluence_url"],
                access_token=access_token,
                auth_type="oauth2",
            )
        else:
            # Basic auth
            confluence_client = ConfluenceClient(
                base_url=st.session_state["confluence_url"],
                email=st.session_state.get("confluence_email"),
                api_token=st.session_state.get("confluence_token"),
                auth_type="basic",
            )

        # Get spaces
        with st.spinner("Loading spaces..."):
            spaces = confluence_client.get_spaces()

        if not spaces:
            st.warning("No spaces found or you have no access to any spaces.")
            return

        # Space selector
        space_names = [space["name"] for space in spaces]
        space_dict = {space["name"]: space for space in spaces}

        selected_space_name = st.selectbox("Select a Space", space_names)

        if selected_space_name:
            selected_space = space_dict[selected_space_name]

            # Get pages in selected space
            with st.spinner(f"Loading pages from {selected_space_name}..."):
                pages = confluence_client.get_pages_in_space(selected_space["key"])

            if not pages:
                st.info(f"No pages found in {selected_space_name}")
                return

            # Display pages for selection
            st.subheader("Select Pages to Ingest")

            # Create a list of page options
            page_options = [f"{page['title']} (ID: {page['id']})" for page in pages]

            selected_pages = st.multiselect(
                "Choose one or more pages to ingest:",
                options=page_options,
                key="confluence_pages_select",
            )

            # Include child pages option
            include_children = st.checkbox(
                "Also include child pages of selected pages",
                value=False,
                key="confluence_include_children",
            )

            if selected_pages:
                # Extract page IDs from selected options
                selected_page_ids = [
                    pages[page_options.index(page)]["id"] for page in selected_pages
                ]

                if st.button(
                    f"Ingest {len(selected_pages)} Page(s)",
                    key="confluence_ingest_button",
                ):
                    with st.spinner(
                        "Processing and uploading Confluence pages to knowledge base..."
                    ):
                        try:
                            if auth_type == "oauth2":
                                successful, errors = process_confluence_pages(
                                    base_url=st.session_state["confluence_url"],
                                    access_token=token_data.get("access_token"),
                                    page_ids=selected_page_ids,
                                    include_children=include_children,
                                    auth_type="oauth2",
                                )
                            else:
                                successful, errors = process_confluence_pages(
                                    base_url=st.session_state["confluence_url"],
                                    email=st.session_state.get("confluence_email"),
                                    api_token=st.session_state.get("confluence_token"),
                                    page_ids=selected_page_ids,
                                    include_children=include_children,
                                    auth_type="basic",
                                )

                            if successful:
                                st.success(
                                    f"✓ Successfully ingested {len(successful)} page(s):\n"
                                    + "\n".join([f"  - {title}" for title in successful])
                                    + "\n\nEmbeddings computation in progress. This is an asynchronous process and may take a few minutes to complete."
                                )

                            if errors:
                                st.warning(f"⚠ {len(errors)} page(s) could not be processed:")
                                for page_id, error_msg in errors:
                                    st.write(f"  - Page {page_id}: {error_msg}")

                        except Exception as e:
                            logger.error(f"Error processing Confluence pages: {traceback.format_exc()}")
                            st.error(
                                f"✗ Error processing Confluence pages: {str(e)}"
                            )

        # Logout button
        if st.button("Disconnect from Confluence", key="confluence_logout"):
            st.session_state["confluence_authenticated"] = False
            st.session_state.pop("confluence_url", None)
            st.session_state.pop("confluence_email", None)
            st.session_state.pop("confluence_token", None)
            st.session_state.pop("confluence_token_data", None)
            st.session_state.pop("confluence_auth_type", None)
            st.rerun()

    except Exception as e:
        logger.error(f"Error in page selector: {traceback.format_exc()}")
        st.error(f"✗ Error loading Confluence data: {str(e)}")
        if st.button("Reconnect", key="confluence_reconnect"):
            st.session_state["confluence_authenticated"] = False
            st.rerun()



try:
    with st.expander("Add documents in Batch", expanded=True):
        config = ConfigHelper.get_active_config_or_default()
        file_type = [
            processor.document_type for processor in config.document_processors
        ]
        uploaded_files = st.file_uploader(
            "Upload a document to add it to the Azure Storage Account, compute embeddings and add them to the Azure AI Search index. Check your configuration for available document processors.",
            type=file_type,
            accept_multiple_files=True,
        )
        blob_client = AzureBlobStorageClient()
        if uploaded_files is not None:
            for up in uploaded_files:
                # To read file as bytes:
                bytes_data = up.getvalue()
                title = sanitize_metadata_value(up.name)
                if st.session_state.get("filename", "") != up.name:
                    # Upload a new file
                    st.session_state["filename"] = up.name
                    st.session_state["file_url"] = blob_client.upload_file(
                        bytes_data, up.name, metadata={"title": title}
                    )
            if len(uploaded_files) > 0:
                st.success(
                    f"{len(uploaded_files)} documents uploaded. Embeddings computation in progress. \nPlease note this is an asynchronous process and may take a few minutes to complete.\nYou can check for further details in the Azure Function logs."
                )

        col1, col2, col3 = st.columns([2, 1, 2])
        with col3:
            st.button(
                "Reprocess all documents in the Azure Storage account",
                on_click=reprocess_all,
            )

    with st.expander("Add URLs to the knowledge base", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text_area(
                "Add URLs and then click on 'Compute Embeddings'",
                placeholder="PLACE YOUR URLS HERE SEPARATED BY A NEW LINE",
                height=100,
                key="urls",
            )

        with col2:
            st.selectbox(
                "Embeddings models",
                [env_helper.AZURE_OPENAI_EMBEDDING_MODEL],
                disabled=True,
            )
            st.button(
                "Process and ingest web pages",
                on_click=add_urls,
                key="add_url",
            )

    with st.expander("Add Confluence pages to the knowledge base", expanded=False):
        st.markdown(
            "Login to your Confluence account and select pages to ingest into the knowledge base."
        )

        if not st.session_state.get("confluence_authenticated"):
            handle_confluence_auth()
        else:
            st.success(
                f"✓ Connected to: {st.session_state.get('confluence_url')}"
            )
            display_confluence_page_selector()

except Exception:
    st.error(traceback.format_exc())
