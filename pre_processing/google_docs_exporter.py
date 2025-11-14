"""Export Google Documents to DOCX format using OAuth2 authentication."""
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleDocsExporter:
    """Export Google Documents to DOCX format with OAuth2 authentication."""

    def __init__(
        self,
        credentials_file: str,
        token_file: str,
        scopes: list,
        output_dir: str = "./google_docs_exports",
    ):
        """
        Initialize Google Docs exporter.

        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store/load refresh token
            scopes: List of Google API scopes to request
            output_dir: Directory to save exported DOCX files

        Example:
            exporter = GoogleDocsExporter(
                credentials_file='./credentials.json',
                token_file='./token.json',
                scopes=['https://www.googleapis.com/auth/drive.readonly'],
                output_dir='./exports'
            )
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = scopes
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.creds: Optional[Credentials] = None
        self.drive_service = None

        logger.info(f"Google Docs exporter initialized with output dir: {output_dir}")

    def authenticate(self) -> bool:
        """
        Authenticate with Google API using OAuth2.

        Returns:
            True if authentication successful, False otherwise

        Process:
            1. Check if token file exists and load saved credentials
            2. If credentials invalid or expired, refresh them
            3. If no valid credentials, run OAuth2 flow (opens browser)
            4. Save credentials to token file for future use
            5. Build Google Drive service client

        Note:
            First-time authentication will open a browser window for user consent.
            Subsequent runs will use the saved refresh token.
        """
        try:
            # Check if token file exists
            if os.path.exists(self.token_file):
                logger.info(f"Loading saved credentials from {self.token_file}")
                self.creds = Credentials.from_authorized_user_file(
                    self.token_file, self.scopes
                )

            # If no valid credentials, authenticate
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refreshing expired credentials...")
                    self.creds.refresh(Request())
                else:
                    # Check if credentials file exists
                    if not os.path.exists(self.credentials_file):
                        logger.error(
                            f"Credentials file not found: {self.credentials_file}"
                        )
                        logger.error(
                            "Please download OAuth2 credentials from Google Cloud Console"
                        )
                        return False

                    logger.info("Running OAuth2 authentication flow...")
                    logger.info("A browser window will open for authentication")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes
                    )
                    self.creds = flow.run_local_server(port=0)

                # Save credentials for future use
                logger.info(f"Saving credentials to {self.token_file}")
                with open(self.token_file, "w") as token:
                    token.write(self.creds.to_json())

            # Build Drive service
            logger.info("Building Google Drive service...")
            self.drive_service = build("drive", "v3", credentials=self.creds)

            logger.info("✅ Authentication successful!")
            return True

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def extract_file_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract Google Docs file ID from URL.

        Args:
            url: Google Docs URL

        Returns:
            File ID if found, None otherwise

        Supported URL formats:
            - https://docs.google.com/document/d/{FILE_ID}/edit
            - https://docs.google.com/document/d/{FILE_ID}/preview
            - https://docs.google.com/document/d/{FILE_ID}
            - {FILE_ID} (raw file ID)

        Examples:
            >>> extract_file_id_from_url('https://docs.google.com/document/d/abc123/edit')
            'abc123'
            >>> extract_file_id_from_url('abc123')
            'abc123'
        """
        # Pattern to match Google Docs URLs
        pattern = r"https://docs\.google\.com/document/d/([a-zA-Z0-9-_]+)"

        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            logger.debug(f"Extracted file ID from URL: {file_id}")
            return file_id

        # If no URL pattern matched, assume it's already a file ID
        # File IDs are alphanumeric with hyphens and underscores
        if re.match(r"^[a-zA-Z0-9-_]+$", url):
            logger.debug(f"Input appears to be a file ID: {url}")
            return url

        logger.warning(f"Could not extract file ID from: {url}")
        return None

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing invalid characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for filesystem

        Removes: / \\ : * ? " < > |
        """
        # Remove invalid filename characters
        invalid_chars = r'[/\\:*?"<>|]'
        sanitized = re.sub(invalid_chars, "_", filename)

        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(". ")

        # Limit length (255 is max for most filesystems, leave room for extension)
        max_length = 240
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    def export_single_document(
        self, file_id_or_url: str, output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export a single Google Document to DOCX format.

        Args:
            file_id_or_url: Google Docs file ID or URL
            output_filename: Custom output filename (optional, uses doc title if not provided)

        Returns:
            Dictionary with export results:
                {
                    'success': bool,
                    'file_path': str (path to exported file if successful),
                    'title': str (document title),
                    'error': str (error message if failed)
                }

        Example:
            result = exporter.export_single_document(
                'https://docs.google.com/document/d/abc123/edit',
                'my_document.docx'
            )
            if result['success']:
                print(f"Exported to: {result['file_path']}")
        """
        result = {"success": False, "file_path": None, "title": None, "error": None}

        try:
            # Authenticate if not already authenticated
            if not self.drive_service:
                if not self.authenticate():
                    result["error"] = "Authentication failed"
                    return result

            # Extract file ID from URL
            file_id = self.extract_file_id_from_url(file_id_or_url)
            if not file_id:
                result["error"] = f"Invalid file ID or URL: {file_id_or_url}"
                logger.error(result["error"])
                return result

            logger.info(f"Exporting Google Doc: {file_id}")

            # Get document metadata
            logger.debug("Fetching document metadata...")
            file_metadata = (
                self.drive_service.files()
                .get(fileId=file_id, fields="id,name,mimeType")
                .execute()
            )

            doc_title = file_metadata.get("name", "Untitled")
            mime_type = file_metadata.get("mimeType", "")

            result["title"] = doc_title
            logger.info(f"Document title: {doc_title}")

            # Verify it's a Google Doc
            if mime_type != "application/vnd.google-apps.document":
                result["error"] = (
                    f"File is not a Google Document (mimeType: {mime_type})"
                )
                logger.error(result["error"])
                return result

            # Determine output filename
            if output_filename:
                filename = output_filename
                if not filename.endswith(".docx"):
                    filename += ".docx"
            else:
                filename = self._sanitize_filename(doc_title) + ".docx"

            output_path = self.output_dir / filename

            # Export to DOCX format
            logger.info("Exporting document to DOCX format...")
            request = self.drive_service.files().export_media(
                fileId=file_id,
                mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

            # Download file content
            file_content = request.execute()

            # Save to file
            logger.info(f"Saving to: {output_path}")
            with open(output_path, "wb") as f:
                f.write(file_content)

            result["success"] = True
            result["file_path"] = str(output_path)
            logger.info(f"✅ Export successful: {output_path}")

        except HttpError as e:
            error_msg = f"Google API error: {e}"
            if e.resp.status == 404:
                error_msg = f"Document not found (404): {file_id}"
            elif e.resp.status == 403:
                error_msg = f"Permission denied (403): You don't have access to this document"
            result["error"] = error_msg
            logger.error(error_msg)

        except Exception as e:
            result["error"] = f"Unexpected error: {e}"
            logger.error(f"Export failed: {e}")

        return result

    def get_authentication_status(self) -> Dict[str, Any]:
        """
        Get current authentication status.

        Returns:
            Dictionary with authentication info:
                {
                    'authenticated': bool,
                    'token_file_exists': bool,
                    'credentials_file_exists': bool,
                    'service_initialized': bool
                }
        """
        return {
            "authenticated": self.creds is not None and self.creds.valid,
            "token_file_exists": os.path.exists(self.token_file),
            "credentials_file_exists": os.path.exists(self.credentials_file),
            "service_initialized": self.drive_service is not None,
        }
