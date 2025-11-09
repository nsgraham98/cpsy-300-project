# https://black-bay-0df91b50f.3.azurestaticapps.net/

import azure.functions as func
from azure.storage.blob import BlobServiceClient
import pandas as pd
import json
import io
import os
import time
import logging

import data_analysis  # <-- uses run_analysis(df, output_dir="...")

def main(req: func.HttpRequest) -> func.HttpResponse:
    start = time.time()
    logging.info("diet-analysis function started")

    try:
        # 1) Get connection string from env var
        conn_str = os.getenv("AzureWebJobsStorage")
        if not conn_str:
            logging.error("AzureWebJobsStorage environment variable is not set")
            return func.HttpResponse(
                "AzureWebJobsStorage not configured.",
                status_code=500,
            )

        # 2) Connect to storage account + container
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service.get_container_client(
            "app-package-diet-analysis-function-app-213f2b9"
        )
        blob_client = container_client.get_blob_client("All_Diets.csv")  # <-- your blob name

        # 3) Download CSV into a DataFrame
        data = blob_client.download_blob().readall()
        df = pd.read_csv(io.BytesIO(data))

        # 4) Run shared analysis logic (saves plots + returns summary dict)
        #    Use /tmp in Azure Functions for temporary files
        analysis_output_dir = "/tmp/outputs"
        summary = data_analysis.run_analysis(df, output_dir=analysis_output_dir)

        # 5) Prepare JSON-friendly result (summary with metadata)
        result = {
            **summary,  # avg_macros, top_protein from data_analysis.run_analysis
            "metadata": {
                "row_count": int(len(df)),
                "diet_types": int(df["Diet_type"].nunique())
                if "Diet_type" in df.columns
                else None,
                "execution_time_ms": round((time.time() - start) * 1000, 2),
                "plots_output_dir": analysis_output_dir,
            },
        }

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as e:
        logging.exception("Error while processing diets data")
        return func.HttpResponse(
            f"Error while processing diets data: {e}",
            status_code=500,
        )
