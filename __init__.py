import azure.functions as func
from azure.storage.blob import BlobServiceClient
import pandas as pd
import json
import io
import os
import time

def main(req: func.HttpRequest) -> func.HttpResponse:
    start = time.time()

    try:
        # 1) Get connection string from env var (AzureWebJobsStorage is usually set by Azure)
        conn_str = os.getenv("AzureWebJobsStorage")
        if not conn_str:
            return func.HttpResponse(
                "AzureWebJobsStorage not configured.",
                status_code=500
            )

        # 2) Connect to your storage account + container
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service.get_container_client("app-package-diet-analysis-function-app-213f2b9")  # <-- use your container name
        blob_client = container_client.get_blob_client("All_Diets.csv")  # <-- your blob name

        # 3) Download CSV into a DataFrame
        data = blob_client.download_blob().readall()
        df = pd.read_csv(io.BytesIO(data))

        # 4) Do your analysis (simplified version)
        avg_macros = (
            df.groupby("Diet_type")[["Protein(g)", "Carbs(g)", "Fat(g)"]]
              .mean()
              .round(2)
              .reset_index()
        )

        top_protein = (
            df.sort_values("Protein(g)", ascending=False)
              .groupby("Diet_type")
              .head(5)
              .reset_index(drop=True)
        )

        # 5) Prepare JSON-friendly result
        result = {
            "avg_macros": avg_macros.to_dict(orient="records"),
            "top_protein": top_protein.to_dict(orient="records"),
            "metadata": {
                "execution_time_ms": round((time.time() - start) * 1000, 2)
            }
        }

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        # Helpful error message if something goes wrong
        return func.HttpResponse(
            f"Error while processing diets data: {e}",
            status_code=500
        )
