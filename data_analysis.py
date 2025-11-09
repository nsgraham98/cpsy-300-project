import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def run_analysis(df: pd.DataFrame, output_dir="outputs"):
    # Calculate the average macronutrient content for each diet type
    avg_macros = df.groupby('Diet_type')[['Protein(g)', 'Carbs(g)', 'Fat(g)']].mean()

    # Find the top 5 protein-rich recipes for each diet type
    top_protein = df.sort_values('Protein(g)', ascending=False).groupby('Diet_type').head(5)

    # Add new metrics 
    df['Protein_to_Carbs_ratio'] = df['Protein(g)'] / df['Carbs(g)']
    df['Carbs_to_Fat_ratio'] = df['Carbs(g)'] / df['Fat(g)']

    # Ensure output directory
    import os
    os.makedirs(output_dir, exist_ok=True)

    # Bar charts for average macronutrients – save instead of show
    plt.figure()
    sns.barplot(x=avg_macros.index, y=avg_macros['Protein(g)'])
    plt.title('Average Protein by Diet Type')
    plt.ylabel('Average Protein (g)')
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/avg_protein_by_diet.png")
    plt.close()

    plt.figure()
    sns.barplot(x=avg_macros.index, y=avg_macros['Carbs(g)'])
    plt.title('Average Carbs by Diet Type')
    plt.ylabel('Average Carbs (g)')
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/avg_carbs_by_diet.png")
    plt.close()

    plt.figure()
    sns.barplot(x=avg_macros.index, y=avg_macros['Fat(g)'])
    plt.title('Average Fat by Diet Type')
    plt.ylabel('Average Fat (g)')
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/avg_fat_by_diet.png")
    plt.close()

    # Heat map
    corr = df.groupby("Diet_type")[['Protein(g)', 'Carbs(g)', 'Fat(g)']].corr()
    plt.figure(figsize=(12, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", linewidths=0.5)
    plt.title("Macronutrient Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/macro_correlation_heatmap.png")
    plt.close()

    # Scatter plot
    plt.figure(figsize=(12, 6))
    sns.scatterplot(
        data=top_protein,
        x="Cuisine_type",
        y="Protein(g)",
        hue="Diet_type",
    )
    plt.title("Top 5 Protein-Rich Recipes by Cuisine Type")
    plt.xlabel("Cuisines")
    plt.ylabel("Protein (g)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/top_protein_recipes_scatter.png")
    plt.close()

    # Return some summary stats for later reuse (e.g., Azure Function)
    return {
        "avg_macros": avg_macros.reset_index().to_dict(orient="records"),
        "top_protein": top_protein.to_dict(orient="records"),
    }

if __name__ == "__main__":
    run_analysis()
