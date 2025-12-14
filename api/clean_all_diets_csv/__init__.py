import logging
import io
import os
import json
from datetime import datetime, timezone
import hashlib

import azure.functions as func
import pandas as pd
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.cosmos import CosmosClient

from shared_code import data_analysis


def _get_cosmos_client() -> CosmosClient:
    cosmos_url = os.getenv("COSMOS_URL")
    cosmos_key = os.getenv("COSMOS_KEY")
    if not cosmos_url or not cosmos_key:
        raise RuntimeError("COSMOS_URL / COSMOS_KEY env vars are missing.")
    return CosmosClient(cosmos_url, credential=cosmos_key)


def upsert_analysis_cache_to_cosmos(cache_payload: dict):
    """
    Upserts the latest analysis cache into Cosmos DB:
      container = COSMOS_CONTAINER (default: "analysis_cache")
      id = COSMOS_CACHE_ID (default: "latest")
      pk = COSMOS_PARTITION_KEY (default: "analysis")
      payload = cache_payload
    Container partition key path should be /pk
    """
    cosmos_db = os.getenv("COSMOS_DB", "dietdb")
    cosmos_container_name = os.getenv("COSMOS_CONTAINER", "analysis_cache")
    cache_id = os.getenv("COSMOS_CACHE_ID", "latest")
    pk_value = os.getenv("COSMOS_PARTITION_KEY", "analysis")

    client = _get_cosmos_client()
    cosmos_container = client.get_database_client(cosmos_db).get_container_client(cosmos_container_name)

    doc = {
        "id": cache_id,
        "pk": pk_value,  # analysis_cache container partition key path should be /pk
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "payload": cache_payload,
    }

    cosmos_container.upsert_item(doc)


def upsert_recipes_to_cosmos(cleaned_df: pd.DataFrame) -> int:
    """
    Upserts individual recipes into Cosmos DB container 'recipes' (or env override).
    Recommended container partition key path: /Diet_type

    Env vars:
      COSMOS_RECIPES_CONTAINER (default: "recipes")
    """
    cosmos_db = os.getenv("COSMOS_DB", "dietdb")
    recipes_container_name = os.getenv("COSMOS_RECIPES_CONTAINER", "recipes")

    client = _get_cosmos_client()
    container = client.get_database_client(cosmos_db).get_container_client(recipes_container_name)

    # Keep only a subset of useful columns for the search API.
    # Adjust or expand as you like.
    keep_cols = [
        "Recipe_name",
        "Diet_type",
        "Cuisine_type",
        "Calories",
        "Protein(g)",
        "Carbs(g)",
        "Fat(g)",
    ]
    cols = [c for c in keep_cols if c in cleaned_df.columns]

    if "Recipe_name" not in cleaned_df.columns or "Diet_type" not in cleaned_df.columns:
        logging.warning("Recipes upsert skipped: missing Recipe_name or Diet_type in cleaned CSV.")
        return 0

    # Replace NaN with empty string to avoid JSON serialization issues
    rows = cleaned_df[cols].fillna("").to_dict(orient="records")

    upserted = 0
    for r in rows:
        name = str(r.get("Recipe_name", "")).strip()
        diet = str(r.get("Diet_type", "")).strip()

        if not name or not diet:
            continue

        # Stable ID prevents duplicates across re-runs.
        # (Using name+diet is usually enough for this dataset.)
        doc_id = hashlib.sha1(f"{name}|{diet}".encode("utf-8")).hexdigest()

        doc = {
            "id": doc_id,
            **r,
        }

        # If your recipes container partition key is /Diet_type, this is all you need.
        # Cosmos will route by doc["Diet_type"].
        container.upsert_item(doc)
        upserted += 1

    return upserted


def main(inblob: func.InputStream):
    """
    Blob Trigger: fires when All_Diets.csv changes.
    (i) Cleans once and writes All_Diets_clean.csv
    (ii) Computes visualization-ready results once and upserts to analysis_cache
    (iii) Upserts cleaned recipes into Cosmos container 'recipes' for search/filter/pagination
    """
    logging.info(
        "clean_all_diets_csv triggered for blob: %s (%s bytes)",
        inblob.name,
        inblob.length,
    )

    conn_str = os.getenv("AzureWebJobsStorage")
    if not conn_str:
        raise RuntimeError("AzureWebJobsStorage env var is missing.")

    # inblob.name looks like: "<container>/All_Diets.csv"
    container_name = inblob.name.split("/")[0]

    blob_service = BlobServiceClient.from_connection_string(conn_str)
    blob_container = blob_service.get_container_client(container_name)

    # Read incoming blob bytes -> DataFrame
    raw_bytes = inblob.read()
    df = pd.read_csv(io.BytesIO(raw_bytes))

    # (i) Clean
    cleaned = data_analysis.clean_df(df)

    # Write cleaned CSV back to storage
    clean_blob_name = "All_Diets_clean.csv"
    clean_bytes = cleaned.to_csv(index=False).encode("utf-8")

    blob_container.get_blob_client(clean_blob_name).upload_blob(
        clean_bytes,
        overwrite=True,
        content_settings=ContentSettings(content_type="text/csv"),
    )

    logging.info(
        "Wrote cleaned CSV to: %s/%s (rows=%d)",
        container_name,
        clean_blob_name,
        len(cleaned),
    )

    # (iii) Upsert recipe rows into Cosmos 'recipes' container (for data interaction API)
    try:
        upserted = upsert_recipes_to_cosmos(cleaned)
        logging.info(
            "Upserted recipes into Cosmos container '%s' (count=%d).",
            os.getenv("COSMOS_RECIPES_CONTAINER", "recipes"),
            upserted,
        )
    except Exception:
        logging.exception("Failed to upsert recipes to Cosmos. Continuing to analysis_cache step...")

    # (ii) Result calculation (cache) — compute once per blob update
    analysis_output_dir = "/tmp/outputs"
    summary = data_analysis.run_analysis(cleaned, output_dir=analysis_output_dir)

    cache_payload = {
        **summary,
        "metadata": {
            "source_blob": inblob.name,
            "clean_blob": f"{container_name}/{clean_blob_name}",
            "row_count": int(len(cleaned)),
            "diet_types": int(cleaned["Diet_type"].nunique()) if "Diet_type" in cleaned.columns else None,
            "cached_utc": datetime.now(timezone.utc).isoformat(),
        },
    }

    # Upsert into Cosmos analysis_cache (this overwrites your seed automatically)
    upsert_analysis_cache_to_cosmos(cache_payload)
    logging.info("Upserted cached analysis to Cosmos (id=%s).", os.getenv("COSMOS_CACHE_ID", "latest"))

    # OPTIONAL: also write blob cache as a fallback during development
    cache_blob_name = "cache/analysis_cache.json"
    blob_container.get_blob_client(cache_blob_name).upload_blob(
        json.dumps(cache_payload).encode("utf-8"),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )
    logging.info("Wrote cached analysis JSON to: %s/%s", container_name, cache_blob_name)
