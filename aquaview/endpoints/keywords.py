def get_keywords(client, limit=None):
    params = {"limit": limit} if limit else None
    return client.get("/api/keywords", params=params)