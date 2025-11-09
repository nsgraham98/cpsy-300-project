import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("All_Diets.csv")

# Calculate the average macronutrient content for each diet type
avg_macros = df.groupby('Diet_type')[['Protein(g)', 'Carbs(g)', 'Fat(g)']].mean()

# Find the top 5 protein-rich recipes for each diet type
top_protein = df.sort_values('Protein(g)', ascending=False).groupby('Diet_type').head(5)

# Add new metrics 
# Protein-to-carbs ratio
df['Protein_to_Carbs_ratio'] = df['Protein(g)'] / df['Carbs(g)']
# Carbs-to-fat ratio
df['Carbs_to_Fat_ratio'] = df['Carbs(g)'] / df['Fat(g)']

# Bar charts for average macronutrients
# Protein
sns.barplot(x=avg_macros.index, y=avg_macros['Protein(g)'])
plt.title('Average Protein by Diet Type')
plt.ylabel('Average Protein (g)')
plt.show()
# Carbs
sns.barplot(x=avg_macros.index, y=avg_macros['Carbs(g)'])
plt.title('Average Carbs by Diet Type')
plt.ylabel('Average Carbs (g)')
plt.show()
# Fat 
sns.barplot(x=avg_macros.index, y=avg_macros['Fat(g)'])
plt.title('Average Fat by Diet Type')
plt.ylabel('Average Fat (g)')
plt.show()

# Heat map for macronutrient correlations
# Compute correlation matrix
corr = df.groupby("Diet_type")[['Protein(g)', 'Carbs(g)', 'Fat(g)']].corr()
# Plot heatmap
plt.figure(figsize=(12,6))
sns.heatmap(corr, annot=True, cmap="coolwarm", linewidths=0.5)
plt.title("Macronutrient Correlation Heatmap")
plt.show()

# Scatter plot for top 5 protein-rich recipes
plt.figure(figsize=(12,6))
sns.scatterplot(
    data=top_protein,
    x="Cuisine_type",
    y="Protein(g)",
    hue="Diet_type",
)
plt.title("Top 5 Protein-Rich Recipes by Cuisine Type")
plt.xlabel("Cuisines")
plt.ylabel("Protein (g)")

plt.show()