# 🌊 Aquaview Python SDK

The **Aquaview Python SDK** is a lightweight, public Python library for interacting with the AQUAVIEW API—a unified access platform for oceanographic datasets from ERDDAP-based sources such as AOOS, IOOS, NOAA, BCO-DMO, and more. This SDK enables seamless search, preview, and retrieval of marine data using simple Python methods.

---

## 🚀 Features

- ✅ Fetch all available data sources
- ✅ List and filter datasets by source, region, time, keywords, and more
- ✅ Retrieve detailed metadata for any dataset
- ✅ Download dataset files in formats like `.nc`, `.csv`, `.json`
- ✅ Get dataset previews in tabular (`pandas`) format
- ✅ Fetch map preview coordinates for visualization
- ✅ Access common metadata tags like `keywords` and `cdm_data_types`

---

## 📦 Installation

Install via PyPI (latest version):

```bash
pip install aquaview

Or install from source:

git clone https://github.com/safaksm/aqualink.git
cd aqualink
pip install .

Or using tarball:

pip install aquaview-0.1.9.tar.gz
```

## 🔧 Usage
**🧪 Quick Example**

```bash
from aquaview import (
    AquaviewClient,
    get_sources,
    get_datasets,
    get_dataset_detail,
    get_dataset_files,
    get_preview_coordinates,
    get_keywords,
    get_cdm_data_types
)

client = AquaviewClient(base_url="https://aqualink-one.vercel.app")


print("\n" + "="*20)
print("🔍 Testing get_sources()")
try:
    sources = get_sources(client)
    print(f"✅ Fetched {len(sources)} sources")
    for s in sources[:3]:
        print(f"- {s['source_id']} | {s['source_name']}")
except Exception as e:
    print(f"❌ get_sources() failed: {e}")


print("\n" + "="*20)
print("🔍 Testing get_datasets()")
try:
    if sources:
        datasets = get_datasets(client, source=sources[0]['source_id'], limit=3)
        print(f"✅ Found {len(datasets)} datasets for source {sources[0]['source_id']}")
        for d in datasets:
            print(f"- {d['dataset_id']} | {d['title']}")
    else:
        print("⚠️ Skipping get_datasets: no sources available")
except Exception as e:
    print(f"❌ get_datasets() failed: {e}")


print("\n" + "="*20)
print("🔍 Testing get_dataset_detail()")
try:
    if datasets:
        detail = get_dataset_detail(client, source=sources[0]['source_id'], dataset_id=datasets[0]['dataset_id'])
        print(f"✅ Dataset title: {detail.get('title', 'N/A')}")
    else:
        print("⚠️ Skipping get_dataset_detail: no datasets available")
except Exception as e:
    print(f"❌ get_dataset_detail() failed: {e}")


print("\n" + "="*20)
print("🔍 Testing get_dataset_files()")
try:
    if datasets:
        files = get_dataset_files(client, source=sources[0]['source_id'], dataset_id=datasets[0]['dataset_id'])
        print(f"✅ Found {len(files)} files")
        for f in files[:2]:
            print(f"- {f['title']} | {f['download_url']}")
    else:
        print("⚠️ Skipping get_dataset_files: no datasets available")
except Exception as e:
    print(f"❌ get_dataset_files() failed: {e}")


print("\n" + "="*20)
print("🔍 Testing get_preview_coordinates()")
try:
    coords = get_preview_coordinates(client)
    print(f"✅ Found {len(coords)} coordinates")
    print(coords[:3])
except Exception as e:
    print(f"❌ get_preview_coordinates() failed: {e}")


print("\n" + "="*20)
print("🔍 Testing get_keywords()")
try:
    keywords = get_keywords(client)
    print(f"✅ Found {len(keywords)} keywords")
    print(keywords[:5])
except Exception as e:
    print(f"❌ get_keywords() failed: {e}")


print("\n" + "="*20)
print("🔍 Testing get_cdm_data_types()")
try:
    cdm_types = get_cdm_data_types(client)
    print(f"✅ Found {len(cdm_types)} cdm_data_types")
    print(cdm_types)
except Exception as e:
    print(f"❌ get_cdm_data_types() failed: {e}")
```


## 📚 API Reference

### `AquaviewClient(base_url)`
**Initializes** a client to communicate with the AQUAVIEW API.

### `get_sources(client)`
**Returns** a list of all available data sources.

### `get_datasets(client, source=None, lat_min=None, lat_max=None, lon_min=None, lon_max=None, limit=None, keywords=None, cdm_data_types=None, search_query=None, time_start=None, time_end=None)`
**Returns** a list of datasets filtered by source, spatial bounds, keyword tags, date range, and more.

### `get_dataset_detail(client, source, dataset_id)`
**Returns** detailed metadata (title, abstract, variables, etc.) for the specified dataset.

### `get_dataset_files(client, source, dataset_id)`
**Returns** downloadable dataset files (.csv, .nc, etc.).

### `get_data(client, source, dataset_id)`
**Fetches** the dataset contents in a tabular format.

⚠️ **Note:** This functionality is not yet available but will be included in a future release.

### `get_preview_coordinates(client, source=None)`
**Returns** a list of [lon, lat] coordinates for dataset previews on a map.

### `get_keywords(client, limit=None)`
**Returns** the most common keyword tags used across datasets.

### `get_cdm_data_types(client)`
**Returns** all distinct cdm_data_type values (e.g., TimeSeries, Grid, Trajectory).


## 🌍 Architecture Overview
```bash
aquaview/
├── client.py         # Core API wrapper class
├── endpoints/        # Individual endpoint logic (modular)
├── utils.py          # Shared utilities
├── exceptions.py     # Error handling
└── __init__.py       # Exports all functions

    Native support for pandas and xarray-ready formats

    Graceful error handling using custom Python exceptions

    Fully compatible with both interactive notebooks and production scripts
```

## 🧪 Testing

The test suite is under development. For now, try the usage example above to validate functionality. Full testing instructions will be provided in a future release.


## 🤝 Contributing

    Clone the repo and create a new branch:

git checkout -b my-feature

Make your changes and push:

    git push origin my-feature

    Submit a pull request into the main branch for review.

## 📅 Roadmap
```bash
CLI support for command-line dataset access

Auto-pagination for large dataset retrieval

Built-in caching for improved performance

Jupyter Notebook widgets for map previews
```
---

## 🧠 Credits

Developed by [Pappu Jha](https://jhapappu.com.np/) as part of the Institute for Advanced Analytics and Security ([IAAS](https://www.usm.edu/advanced-analytics-security/)) research program.

---

## 📄 License

MIT License – see [LICENSE](https://opensource.org/license/mit) for full details.
