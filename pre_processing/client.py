"""ServiceNow API client for making authenticated requests."""
import requests
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ServiceNowClient:
    """Client for interacting with ServiceNow REST API."""
    
    def __init__(self, instance: str, username: str, password: str, timeout: int = 30):
        """
        Initialize ServiceNow client.
        
        Args:
            instance: ServiceNow instance URL (e.g., 'yourcompany.service-now.com')
            username: ServiceNow username
            password: ServiceNow password
            timeout: Request timeout in seconds
        """
        self.instance = instance.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.base_url = f"https://{self.instance}/api/now"
        
        # Setup session for connection pooling
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        """
        Make GET request to ServiceNow API.
        
        Args:
            endpoint: API endpoint (e.g., 'table/kb_knowledge')
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            requests.exceptions.RequestException: If request fails
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.debug(f"GET request to {url} with params: {params}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making GET request to {url}: {e}")
            raise
    
    def get_attachment(self, sys_id: str) -> bytes:
        """
        Download attachment content by sys_id.
        
        Args:
            sys_id: System ID of the attachment
            
        Returns:
            Attachment content as bytes
            
        Raises:
            requests.exceptions.RequestException: If request fails
        """
        url = f"{self.base_url}/attachment/{sys_id}/file"
        
        try:
            logger.debug(f"Downloading attachment from {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading attachment {sys_id}: {e}")
            raise
    
    def query_table(self, table: str, query: Optional[str] = None, 
                    fields: Optional[List[str]] = None, 
                    limit: Optional[int] = None,
                    offset: int = 0) -> List[Dict]:
        """
        Query a ServiceNow table.
        
        Args:
            table: Table name (e.g., 'kb_knowledge')
            query: Encoded query string
            fields: List of fields to return
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of records
        """
        params: Dict[str, Any] = {
            'sysparm_offset': offset
        }
        
        if query:
            params['sysparm_query'] = query
        
        if fields:
            params['sysparm_fields'] = ','.join(fields)
        
        if limit:
            params['sysparm_limit'] = limit
        
        endpoint = f"table/{table}"
        response = self.get(endpoint, params=params)
        return response.get('result', [])
    
    def get_record(self, table: str, sys_id: str, 
                   fields: Optional[List[str]] = None) -> Dict:
        """
        Get a single record by sys_id.
        
        Args:
            table: Table name
            sys_id: System ID of the record
            fields: List of fields to return
            
        Returns:
            Record data
        """
        params = {}
        if fields:
            params['sysparm_fields'] = ','.join(fields)
        
        endpoint = f"table/{table}/{sys_id}"
        response = self.get(endpoint, params=params)
        return response.get('result', {})
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

