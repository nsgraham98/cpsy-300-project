# https://black-bay-0df91b50f.3.azurestaticapps.net/

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
import pandas as pd
import json
import io
import os
import time
import logging

from shared_code import data_analysis

CONTAINER_NAME = "app-package-diet-analysis-function-app-213f2b9"
CACHE_BLOB_NAME = "cache/analysis_cache.json"


def _download_csv(container_client, preferred_blob: str, fallback_blob: str) -> pd.DataFrame:
    """Fallback path only (used if cache missing)."""
    try:
        b = container_client.get_blob_client(preferred_blob)
        data = b.download_blob().readall()
        logging.info("Loaded preferred CSV blob: %s", preferred_blob)
        return pd.read_csv(io.BytesIO(data))
    except Exception as e:
        logging.warning("Preferred CSV missing/failed (%s). Falling back to %s. Error: %s",
                        preferred_blob, fallback_blob, e)
        b = container_client.get_blob_client(fallback_blob)
        data = b.download_blob().readall()
        return pd.read_csv(io.BytesIO(data))
    
def read_analysis_cache_from_cosmos():
    cosmos_url = os.getenv("COSMOS_URL")
    cosmos_key = os.getenv("COSMOS_KEY")
    cosmos_db = os.getenv("COSMOS_DB", "dietdb")
    cosmos_container = os.getenv("COSMOS_CONTAINER", "analysis_cache")
    cache_id = os.getenv("COSMOS_CACHE_ID", "latest")
    pk_value = os.getenv("COSMOS_PARTITION_KEY", "analysis")

    if not cosmos_url or not cosmos_key:
        return None

    client = CosmosClient(cosmos_url, credential=cosmos_key)
    container = client.get_database_client(cosmos_db).get_container_client(cosmos_container)

    try:
        doc = container.read_item(item=cache_id, partition_key=pk_value)
        return doc.get("payload")
    except Exception:
        return None


def main(req: func.HttpRequest) -> func.HttpResponse:
    start = time.time()
    logging.info("diet-analysis function started")

    try:
        # 0) FASTEST PATH: Cosmos DB cache
        try:
            cosmos_payload = read_analysis_cache_from_cosmos()
            if cosmos_payload:
                cosmos_payload.setdefault("metadata", {})
                cosmos_payload["metadata"]["api_execution_time_ms"] = round((time.time() - start) * 1000, 2)
                cosmos_payload["metadata"]["cache_source"] = "cosmos"
                return func.HttpResponse(
                    json.dumps(cosmos_payload),
                    mimetype="application/json",
                    status_code=200,
                )
        except Exception as e:
            logging.warning("Cosmos cache read failed. Falling back. Error: %s", e)

        # 1) Storage connection (needed for blob fallback + compute fallback)
        conn_str = os.getenv("AzureWebJobsStorage")
        if not conn_str:
            logging.error("AzureWebJobsStorage environment variable is not set")
            return func.HttpResponse("AzureWebJobsStorage not configured.", status_code=500)

        blob_service = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service.get_container_client(CONTAINER_NAME)

        # 2) Blob cache fallback (optional but useful during setup)
        try:
            cache_bytes = (
                container_client
                .get_blob_client(CACHE_BLOB_NAME)
                .download_blob()
                .readall()
            )
            payload = json.loads(cache_bytes)
            payload.setdefault("metadata", {})
            payload["metadata"]["api_execution_time_ms"] = round((time.time() - start) * 1000, 2)
            payload["metadata"]["cache_source"] = "blob"
            return func.HttpResponse(
                json.dumps(payload),
                mimetype="application/json",
                status_code=200,
            )
        except Exception as e:
            logging.warning("Blob cache not available (%s). Falling back to compute. Error: %s",
                            CACHE_BLOB_NAME, e)

        # 3) LAST RESORT: compute on-demand
        df = _download_csv(container_client, "All_Diets_clean.csv", "All_Diets.csv")

        analysis_output_dir = "/tmp/outputs"
        summary = data_analysis.run_analysis(df, output_dir=analysis_output_dir)

        result = {
            **summary,
            "metadata": {
                "row_count": int(len(df)),
                "diet_types": int(df["Diet_type"].nunique()) if "Diet_type" in df.columns else None,
                "execution_time_ms": round((time.time() - start) * 1000, 2),
                "plots_output_dir": analysis_output_dir,
                "cache_status": "miss (computed on-demand)",
                "cache_source": "computed",
            },
        }

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as e:
        logging.exception("Error while processing diets data")
        return func.HttpResponse(f"Error while processing diets data: {e}", status_code=500)
