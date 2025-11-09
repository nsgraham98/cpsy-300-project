# analyze_diets/__init__.py
import azure.functions as func
import json
import os
import io
import pandas as pd
from azure.storage.blob import BlobServiceClient
from data_analysis import run_analysis  # reuse your logic

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        conn_str = os.getenv("AzureWebJobsStorage")
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        container = blob_service.get_container_client("diets")
        blob = container.download_blob("All_Diets.csv")

        # Load into DataFrame
        df = pd.read_csv(io.BytesIO(blob.readall()))

        # Slight tweak: let run_analysis accept a DataFrame instead of path
        # you can overload it or move part of the logic here:
        # summary = run_analysis_from_df(df)
        # return func.HttpResponse(
        #     json.dumps(summary),
        #     mimetype="application/json"
        # )
        analysis = run_analysis(df, output_dir="/tmp")
        return func.HttpResponse(
            json.dumps(analysis),
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            f"Error: {e}",
            status_code=500
        )

def run_analysis_from_df(df: pd.DataFrame):
    # This mirrors the logic inside run_analysis but without re-reading CSV
    avg_macros = df.groupby('Diet_type')[['Protein(g)', 'Carbs(g)', 'Fat(g)']].mean()
    top_protein = df.sort_values('Protein(g)', ascending=False).groupby('Diet_type').head(5)

    df['Protein_to_Carbs_ratio'] = df['Protein(g)'] / df['Carbs(g)']
    df['Carbs_to_Fat_ratio'] = df['Carbs(g)'] / df['Fat(g)']

    return {
        "avg_macros": avg_macros.reset_index().to_dict(orient="records"),
        "top_protein": top_protein.to_dict(orient="records"),
    }
