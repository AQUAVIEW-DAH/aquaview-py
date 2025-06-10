# Aquaview SDK

A Python wrapper for the AQUAVIEW API.

## Installation
```bash
pip install -e .
```

## Usage
```python
from aquaview import AquaviewClient, get_datasets

client = AquaviewClient(base_url="https://api.aquaview.org")
data = get_datasets(client, keywords=["ocean"], limit=5)
print(data)
```

## License
MIT