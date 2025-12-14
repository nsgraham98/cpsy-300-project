import os
import json
import logging
import azure.functions as func
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

def _get_container():
    endpoint = os.getenv("COSMOS_URL")
    key = os.getenv("COSMOS_KEY")
    db_name = os.getenv("COSMOS_DB_NAME", "dietdb")
    container_name = os.getenv("COSMOS_RECIPES_CONTAINER", "recipes")

    if not endpoint or not key:
        raise RuntimeError("Missing COSMOS_URL or COSMOS_KEY in app settings")

    client = CosmosClient(endpoint, credential=key)
    db = client.get_database_client(db_name)
    return db.get_container_client(container_name)

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        container = _get_container()

        diet = (req.params.get("diet") or "").strip()
        q = (req.params.get("q") or "").strip().lower()

        # pageSize (default 10, clamp 1..50)
        page_size_raw = req.params.get("pageSize", "10")
        try:
            page_size = max(1, min(50, int(page_size_raw)))
        except ValueError:
            page_size = 10

        # page (default 1, clamp >= 1)
        page_raw = req.params.get("page", "1")
        try:
            page = max(1, int(page_raw))
        except ValueError:
            page = 1

        offset = (page - 1) * page_size

        where = []
        params = []

        if diet and diet.lower() != "all":
            where.append("c.Diet_type = @diet")
            params.append({"name": "@diet", "value": diet})

        if q:
            where.append(
                "("
                "CONTAINS(LOWER(c.Recipe_name), @q) "
                "OR CONTAINS(LOWER(c.Cuisine_type), @q)"
                ")"
            )
            params.append({"name": "@q", "value": q})

        # OFFSET/LIMIT parameters (required for this query)
        params.append({"name": "@offset", "value": offset})
        params.append({"name": "@limit", "value": page_size})

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        # NOTE: No continuation tokens in this approach.
        query = (
            f"SELECT * FROM c{where_sql} "
            "ORDER BY c.Recipe_name "
            "OFFSET @offset LIMIT @limit"
        )

        logging.info(
            "recipes query page=%s pageSize=%s offset=%s diet=%r q=%r query=%s params=%s",
            page, page_size, offset, diet, q, query, params
        )

        try:
            items = list(container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            ))
        except CosmosHttpResponseError as e:
            logging.exception("Cosmos query failed")
            return func.HttpResponse(
                json.dumps({"error": "Cosmos query failed", "cosmos": str(e)}),
                status_code=400,
                mimetype="application/json",
            )

        # simple "hasMore" heuristic (if we got a full page, assume there might be more)
        has_more = len(items) == page_size

        return func.HttpResponse(
            json.dumps({
                "items": items,
                "count": len(items),
                "page": page,
                "pageSize": page_size,
                "hasMore": has_more,
                "nextPage": (page + 1) if has_more else None,
            }),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.exception("recipes search failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
