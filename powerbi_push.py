import os, requests

def push_dataframe_to_powerbi(df):
    url = os.getenv("PBI_DATASET_URL")  # ex.: https://api.powerbi.com/beta/{tenant}/datasets/{id}/rows?key=...
    token = os.getenv("PBI_BEARER_TOKEN")  # opcional: Bearer token
    if not url:
        raise RuntimeError("PBI_DATASET_URL não definido")
    rows = df.to_dict(orient="records")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.post(url, json={"rows": rows}, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.status_code