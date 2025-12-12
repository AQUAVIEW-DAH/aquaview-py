"""
Aquaview Python SDK Client

A simple client for interacting with the AQUAVIEW API.
"""

import requests
from typing import Optional, Dict, List, Any


class AquaviewError(Exception):
    """Exception raised for Aquaview API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AquaviewClient:
    """
    Client for interacting with the AQUAVIEW API.
    
    Args:
        base_url: Base URL for the API (default: https://service.aquaview.org)
        api_key: Optional API key for authenticated requests
    
    Example:
        >>> client = AquaviewClient()
        >>> sources = client.get_sources()
        >>> results = client.search(q="glider", size=5)
    """
    
    DEFAULT_BASE_URL = "https://service.aquaview.org"
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.headers = {"Accept": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    def _request(self, method: str, endpoint: str, params: Dict = None, json: Dict = None) -> Any:
        """Make an HTTP request to the API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            try:
                error_detail = e.response.json().get('detail', str(e))
            except Exception:
                error_detail = str(e)
            raise AquaviewError(f"API Error: {error_detail}", status_code)
        except requests.exceptions.RequestException as e:
            raise AquaviewError(f"Request failed: {str(e)}")
    
    def _get(self, endpoint: str, params: Dict = None) -> Any:
        """Make a GET request."""
        return self._request("GET", endpoint, params=params)
    
    def _post(self, endpoint: str, json: Dict = None) -> Any:
        """Make a POST request."""
        return self._request("POST", endpoint, json=json)
    
    # -------------------------------------------------------------------------
    # API Methods
    # -------------------------------------------------------------------------
    
    def get_status(self) -> Dict:
        """
        Get API status and health information.
        
        Returns:
            Dict with API name, version, status, and loaded adapters
        """
        return self._get("/status")
    
    def get_sources(self) -> List[Dict]:
        """
        Get list of available data sources.
        
        Returns:
            List of source dictionaries with 'source_id' and 'source_name'
        
        Example:
            >>> sources = client.get_sources()
            >>> for s in sources:
            ...     print(f"{s['source_id']}: {s['source_name']}")
        """
        return self._get("/api/sources")
    
    def search(
        self,
        q: Optional[str] = None,
        bbox: Optional[str] = None,
        location: Optional[str] = None,
        radius: Optional[str] = None,
        t0: Optional[str] = None,
        t1: Optional[str] = None,
        variables: Optional[str] = None,
        source: Optional[str] = None,
        platform_type: Optional[str] = None,
        institution: Optional[str] = None,
        size: int = 75,
        cursor: Optional[str] = None,
        pit: Optional[str] = None,
        zoom: int = 8,
        generate_tiles: bool = False,
    ) -> Dict:
        """
        Search for datasets with various filters.
        
        This is the primary search endpoint for finding oceanographic datasets.
        
        Args:
            q: Text search query (e.g., "glider", "temperature")
            bbox: Bounding box as "lon_min,lat_min,lon_max,lat_max"
            location: Center point as "lat,lon" for radius search
            radius: Search radius with units (e.g., "50km", "100mi")
            t0: Start time in ISO format (e.g., "2020-01-01T00:00:00Z")
            t1: End time in ISO format (e.g., "2020-12-31T23:59:59Z")
            variables: Comma-separated variable names (e.g., "temperature,salinity")
            source: Comma-separated source IDs (e.g., "IOOS,WOD")
            platform_type: Platform type filter (e.g., "moored_buoy", "glider")
            institution: Institution filter
            size: Number of results per page (1-2500, default: 75)
            cursor: Pagination cursor from previous response
            pit: Point-in-time ID for consistent pagination
            zoom: Map zoom level for tile aggregation (default: 8)
            generate_tiles: Generate geo-tile aggregations (default: False)
        
        Returns:
            Dict containing:
                - total: Total number of matching datasets
                - data: List of dataset objects
                - next_cursor: Cursor for next page (None if no more pages)
                - pit: Point-in-time ID for pagination
                - aggs: Aggregations (if generate_tiles=True)
        
        Example:
            >>> # Simple text search
            >>> results = client.search(q="glider", size=10)
            >>> print(f"Found {results['total']} datasets")
            
            >>> # Geographic search
            >>> results = client.search(location="42.3,-70.5", radius="100km")
            
            >>> # Time-filtered search
            >>> results = client.search(
            ...     variables="temperature",
            ...     t0="2020-01-01T00:00:00Z",
            ...     t1="2020-12-31T23:59:59Z"
            ... )
        """
        params = {"size": size, "zoom": zoom, "generate_tiles": str(generate_tiles).lower()}
        
        if q:
            params["q"] = q
        if bbox:
            params["bbox"] = bbox
        if location:
            params["location"] = location
        if radius:
            params["radius"] = radius
        if t0:
            params["t0"] = t0
        if t1:
            params["t1"] = t1
        if variables:
            params["variables"] = variables
        if source:
            params["source"] = source
        if platform_type:
            params["platform_type"] = platform_type
        if institution:
            params["institution"] = institution
        if cursor:
            params["cursor"] = cursor
        if pit:
            params["pit"] = pit
        
        return self._get("/api/search", params=params)
    
    def get_dataset_detail(self, source: str, dataset_id: str) -> Dict:
        """
        Get detailed information about a specific dataset.
        
        Args:
            source: Source identifier (e.g., "IOOS", "WOD", "GLOS")
            dataset_id: Dataset identifier
        
        Returns:
            Dict containing full dataset metadata including:
                - title, summary, institution
                - citation information
                - variables list
                - time coverage
                - geographic coverage
        
        Example:
            >>> detail = client.get_dataset_detail("IOOS", "whoi_406-20160902T1700")
            >>> print(detail['title'])
            >>> print(detail['citation'])
        """
        return self._get(f"/api/datasets/{source}/{dataset_id}")
    
    def get_dataset_files(self, source: str, dataset_id: str) -> List[Dict]:
        """
        Get available file formats and download URLs for a dataset.
        
        Args:
            source: Source identifier (e.g., "IOOS", "WOD")
            dataset_id: Dataset identifier
        
        Returns:
            List of file dictionaries containing:
                - path: File path
                - download_url: Direct download URL
                - title: Description of the file format
        
        Example:
            >>> files = client.get_dataset_files("IOOS", "whoi_406-20160902T1700")
            >>> for f in files:
            ...     print(f"{f['path']}: {f['download_url']}")
        """
        return self._get(f"/api/datasets/{source}/{dataset_id}/files")
    
    def search_all(self, **kwargs) -> List[Dict]:
        """
        Search and retrieve ALL matching datasets (handles pagination automatically).
        
        Warning: This may take a while for large result sets!
        
        Args:
            **kwargs: Same parameters as search()
        
        Returns:
            List of all matching dataset objects
        
        Example:
            >>> all_gliders = client.search_all(q="glider", source="IOOS")
            >>> print(f"Found {len(all_gliders)} total glider datasets")
        """
        all_data = []
        pit = None
        cursor = None
        
        while True:
            response = self.search(**kwargs, pit=pit, cursor=cursor)
            all_data.extend(response.get('data', []))
            
            pit = response.get('pit')
            cursor = response.get('next_cursor')
            
            if not cursor:
                break
        
        return all_data
