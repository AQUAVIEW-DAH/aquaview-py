# Aquaview Python SDK

A Python library for accessing oceanographic datasets through the AQUAVIEW API.

**Base URL:** `https://service.aquaview.org`

## Installation

```bash
# Install from source
pip install -e .

# Or install from PyPI
pip install aquaview
```

## Quick Start

```python
from aquaview import AquaviewClient

# Create a client (uses default base URL)
client = AquaviewClient()

# List available data sources
sources = client.get_sources()
for s in sources:
    print(f"{s['source_id']}: {s['source_name']}")

# Search for datasets
results = client.search(q="glider", size=5)
print(f"Found {results['total']} datasets")

for dataset in results['data']:
    print(f"- {dataset['title']}")
```

## Features

- Search datasets by text, location, time range, and variables
- Get detailed dataset metadata including citations
- Get download URLs for various file formats (CSV, NetCDF, JSON, etc.)
- Automatic pagination support
- No authentication required for basic access

## API Reference

### `AquaviewClient`

```python
client = AquaviewClient(
    base_url="https://service.aquaview.org",  # Optional, this is the default
    api_key="your-api-key"  # Optional, for authenticated access
)
```

### `client.get_sources()`

Get list of available data sources.

```python
sources = client.get_sources()
# Returns: [{"source_id": "IOOS", "source_name": "IOOS Glider DAC ERDDAP"}, ...]
```

### `client.search(...)`

Search for datasets with various filters.

```python
# Simple text search
results = client.search(q="temperature", size=10)

# Geographic search (radius)
results = client.search(location="42.3,-70.5", radius="100km")

# Geographic search (bounding box)
results = client.search(bbox="-74.1,40.5,-73.9,40.7")

# Time range search
results = client.search(
    t0="2020-01-01T00:00:00Z",
    t1="2020-12-31T23:59:59Z"
)

# Filter by variables
results = client.search(variables="temperature,salinity")

# Filter by source
results = client.search(source="IOOS,WOD")

# Combined search
results = client.search(
    q="glider",
    location="42.3,-70.5",
    radius="100km",
    variables="temperature",
    t0="2020-01-01T00:00:00Z",
    t1="2020-12-31T23:59:59Z",
    size=20
)
```

**Parameters:**
- `q` - Text search query
- `bbox` - Bounding box: "lon_min,lat_min,lon_max,lat_max"
- `location` - Center point: "lat,lon"
- `radius` - Search radius: "50km", "100mi", etc.
- `t0` - Start time (ISO format)
- `t1` - End time (ISO format)
- `variables` - Comma-separated variable names
- `source` - Comma-separated source IDs
- `platform_type` - Platform type filter
- `institution` - Institution filter
- `size` - Results per page (1-2500, default: 75)
- `cursor` - Pagination cursor
- `pit` - Point-in-time ID for consistent pagination

**Returns:**
```python
{
    "total": 1234,
    "data": [...],  # List of dataset objects
    "next_cursor": "...",  # Use for pagination
    "pit": "..."  # Point-in-time ID
}
```

### `client.get_dataset_detail(source, dataset_id)`

Get detailed metadata for a specific dataset.

```python
detail = client.get_dataset_detail("IOOS", "whoi_406-20160902T1700")
print(detail['title'])
print(detail['summary'])
print(detail['citation'])
print(detail['variables'])
```

### `client.get_dataset_files(source, dataset_id)`

Get available download formats and URLs.

```python
files = client.get_dataset_files("IOOS", "whoi_406-20160902T1700")
for f in files:
    print(f"{f['path']}: {f['download_url']}")
```

### `client.search_all(...)`

Search and retrieve ALL matching datasets (handles pagination automatically).

```python
# Warning: May take a while for large result sets!
all_gliders = client.search_all(q="glider", source="IOOS")
print(f"Found {len(all_gliders)} total datasets")
```

### `client.get_status()`

Get API health status.

```python
status = client.get_status()
print(f"API: {status['name']} v{status['version']}")
print(f"Adapters loaded: {status['adapters_loaded']}")
```

## Complete Example

```python
from aquaview import AquaviewClient

client = AquaviewClient()

# Step 1: Search for glider data near Massachusetts Bay
results = client.search(
    q="glider",
    location="42.3,-70.5",
    radius="100km",
    size=5
)
print(f"Found {results['total']} datasets")

# Step 2: Get details for the first result
if results['data']:
    dataset = results['data'][0]
    source = dataset['source_adapter']
    dataset_id = dataset['dataset_id']
    
    detail = client.get_dataset_detail(source, dataset_id)
    print(f"\nTitle: {detail['title']}")
    print(f"Institution: {detail.get('institution', 'N/A')}")
    print(f"Variables: {', '.join(detail.get('variables', [])[:5])}")
    
    # Step 3: Get download URLs
    files = client.get_dataset_files(source, dataset_id)
    print(f"\nAvailable formats ({len(files)}):")
    for f in files[:3]:
        print(f"  - {f['download_url']}")
```

## Error Handling

```python
from aquaview import AquaviewClient, AquaviewError

client = AquaviewClient()

try:
    detail = client.get_dataset_detail("INVALID", "nonexistent")
except AquaviewError as e:
    print(f"Error: {e.message}")
    print(f"Status code: {e.status_code}")
```

## License

MIT License
