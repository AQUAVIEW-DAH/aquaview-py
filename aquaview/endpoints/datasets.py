def get_datasets(client, **filters):
    return client.get("/api/datasets", params=filters)

def get_dataset_detail(client, source: str, dataset_id: str):
    return client.get(f"/api/datasets/{source}/{dataset_id}")

def get_dataset_files(client, source: str, dataset_id: str):
    return client.get(f"/api/datasets/{source}/{dataset_id}/files")