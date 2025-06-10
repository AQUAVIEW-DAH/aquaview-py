def get_preview_coordinates(client, source=None):
    params = {"source": source} if source else None
    return client.get("/api/preview", params=params)