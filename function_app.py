import azure.functions as func
import json
import logging
import os
import time
import io

import pandas as pd
from azure.storage.blob import BlobServiceClient

# Create FunctionApp instance
app = func.FunctionApp()


@app.route(route="diet-analysis", auth_level=func.AuthLevel.ANONYMOUS)
def analyze_diets(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("diet-analysis function started")
    start_time = time.time()

    try:
        # 1) Get connection string from environment
        conn_str = os.getenv("AzureWebJobsStorage")
        if not conn_str:
            logging.error("AzureWebJobsStorage environment variable is not set")
            return func.HttpResponse(
                "AzureWebJobsStorage not configured.",
                status_code=500,
            )

        # 2) Connect to Blob Storage
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service.get_container_client("app-package-diet-analysis-function-app-213f2b9")  # <-- your container name
        blob_client = container_client.get_blob_client("All_Diets.csv")  # <-- your blob name

        # 3) Download CSV data
        blob_bytes = blob_client.download_blob().readall()
        df = pd.read_csv(io.BytesIO(blob_bytes))

        # 4) Do analysis

        # Average macronutrients by Diet_type
        avg_macros = (
            df.groupby("Diet_type")[["Protein(g)", "Carbs(g)", "Fat(g)"]]
            .mean()
            .round(2)
            .reset_index()
        )

        # Top 5 protein-rich recipes per Diet_type
        top_protein = (
            df.sort_values("Protein(g)", ascending=False)
              .groupby("Diet_type")
              .head(5)
              .reset_index(drop=True)
        )

        # Optionally add ratios
        if "Protein(g)" in df.columns and "Carbs(g)" in df.columns and "Fat(g)" in df.columns:
            df["Protein_to_Carbs_ratio"] = df["Protein(g)"] / df["Carbs(g)"].replace({0: pd.NA})
            df["Carbs_to_Fat_ratio"] = df["Carbs(g)"] / df["Fat(g)"].replace({0: pd.NA})

        # 5) Build JSON response
        result = {
            "avg_macros": avg_macros.to_dict(orient="records"),
            "top_protein": top_protein.to_dict(orient="records"),
            "metadata": {
                "row_count": int(len(df)),
                "diet_types": df["Diet_type"].nunique(),
                "execution_time_ms": round((time.time() - start_time) * 1000, 2),
            },
        }

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as e:
        logging.exception("Error in diet-analysis function")
        return func.HttpResponse(
            f"Error while processing diets data: {e}",
            status_code=500,
        )
