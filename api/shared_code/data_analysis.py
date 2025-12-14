import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


REQUIRED_COLUMNS = ["Diet_type", "Recipe_name", "Protein(g)", "Carbs(g)", "Fat(g)"]


def _normalize_col(col: str) -> str:
    # Normalize spaces + remove weird invisible chars
    col = (col or "").strip()
    col = re.sub(r"\s+", " ", col)
    return col


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean All_Diets.csv in a safe, repeatable way.
    Runs on blob-change only (via blob trigger), not per HTTP request.
    """
    if df is None or df.empty:
        return df

    # Normalize column names (trim / collapse whitespace)
    df = df.copy()
    df.columns = [_normalize_col(c) for c in df.columns]

    # Drop exact duplicate rows
    df = df.drop_duplicates()

    # Ensure required columns exist (don’t crash if a column is missing)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        # Keep going, but you’ll see this in logs from the function
        # (caller can decide whether to reject)
        pass

    # Strip string columns
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()

    # Coerce macro columns to numeric, and remove obviously bad values
    for c in ["Protein(g)", "Carbs(g)", "Fat(g)"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
            # drop impossible negatives
            df.loc[df[c] < 0, c] = pd.NA

    # Diet_type cleanup
    if "Diet_type" in df.columns:
        df["Diet_type"] = df["Diet_type"].replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})
        df["Diet_type"] = df["Diet_type"].fillna("Unknown")

    # Recipe name cleanup (optional)
    if "Recipe_name" in df.columns:
        df["Recipe_name"] = df["Recipe_name"].replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})
        df["Recipe_name"] = df["Recipe_name"].fillna("Unnamed Recipe")

    # Drop rows missing key data (only if those columns exist)
    drop_keys = [c for c in ["Diet_type", "Recipe_name"] if c in df.columns]
    if drop_keys:
        df = df.dropna(subset=drop_keys)

    # Final reset index
    return df.reset_index(drop=True)


def run_analysis(df: pd.DataFrame, output_dir="outputs"):
    # Calculate the average macronutrient content for each diet type
    avg_macros = df.groupby("Diet_type")[["Protein(g)", "Carbs(g)", "Fat(g)"]].mean()

    # Find the top 5 protein-rich recipes for each diet type
    top_protein = (
        df.sort_values("Protein(g)", ascending=False)
        .groupby("Diet_type")
        .head(5)
    )

    os.makedirs(output_dir, exist_ok=True)

    # (Optional charts) — keep if you still need PNGs somewhere
    # If you don’t use PNGs, you can delete the plotting for speed.

    # Return summary stats
    return {
        "avg_macros": avg_macros.reset_index().to_dict(orient="records"),
        "top_protein": top_protein.reset_index(drop=True).to_dict(orient="records"),
    }


if __name__ == "__main__":
    df = pd.read_csv("data/All_Diets.csv")
    df = clean_df(df)
    run_analysis(df)
