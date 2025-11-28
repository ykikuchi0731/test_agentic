"""Attachment download and management for knowledge base articles."""
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class AttachmentManager:
    """Manage article attachments and downloads."""

    def __init__(self, client, download_dir: str = "./downloads"):
        """
        Initialize attachment manager.

        Args:
            client: ServiceNowClient instance
            download_dir: Directory to save downloaded files
        """
        self.client = client
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def get_attachments(
        self, article_sys_id: str, download: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get attached files for an article.

        Args:
            article_sys_id: System ID of the knowledge article
            download: If True, download attachment files to disk

        Returns:
            List of attachment metadata dictionaries
        """
        logger.info(f"Getting attachments for article {article_sys_id}")

        query = f"table_name=kb_knowledge^table_sys_id={article_sys_id}"

        try:
            attachments = self.client.query_table(
                table="sys_attachment",
                query=query,
                fields=[
                    "sys_id",
                    "file_name",
                    "content_type",
                    "size_bytes",
                    "sys_created_on",
                    "download_link",
                ],
            )

            logger.info(f"Found {len(attachments)} attachments")

            if download and attachments:
                self._download_attachments(article_sys_id, attachments)

            return attachments

        except Exception as e:
            logger.error(f"Error getting attachments for article {article_sys_id}: {e}")
            raise

    def get_attachments_for_multiple(
        self, article_sys_ids: List[str], download: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get attachments from multiple articles (e.g., original + translations).

        Args:
            article_sys_ids: List of article system IDs
            download: If True, download attachment files to disk

        Returns:
            Combined list of attachment metadata from all articles
        """
        logger.info(f"Getting attachments for {len(article_sys_ids)} articles")

        all_attachments = []

        for article_sys_id in article_sys_ids:
            try:
                attachments = self.get_attachments(article_sys_id, download=download)
                all_attachments.extend(attachments)
            except Exception as e:
                logger.error(f"Error getting attachments for {article_sys_id}: {e}")
                continue

        logger.info(f"Found total of {len(all_attachments)} attachments across all articles")
        return all_attachments

    def _download_attachments(
        self, article_sys_id: str, attachments: List[Dict[str, Any]]
    ) -> None:
        """
        Download attachment files to disk.

        Args:
            article_sys_id: System ID of the article
            attachments: List of attachment metadata
        """
        # Create article-specific directory
        article_dir = self.download_dir / article_sys_id
        article_dir.mkdir(parents=True, exist_ok=True)

        for attachment in attachments:
            sys_id = attachment["sys_id"]
            file_name = attachment["file_name"]

            try:
                logger.info(f"Downloading attachment: {file_name}")

                # Download file content
                content = self.client.get_attachment(sys_id)

                # Save to disk
                file_path = article_dir / file_name
                file_path.write_bytes(content)

                # Add local file path to attachment metadata
                attachment["file_path"] = str(file_path)

                logger.info(f"Saved attachment to {file_path}")

            except Exception as e:
                logger.error(f"Error downloading attachment {file_name}: {e}")
                attachment["download_error"] = str(e)
