import pandas as pd
import os

# File paths
solar_panel_file_path = 'output/solar_panel_with_mesh_id.csv'
sample_mesh_file_path = 'input/sample_mesh_data.csv'
output_dir = 'output'
output_file_path = os.path.join(output_dir, 'solar_panel_with_average_hail_frequency.csv')

# Load data using Shift-JIS encoding
solar_panel_data = pd.read_csv(solar_panel_file_path, encoding='shift-jis')
sample_mesh_data = pd.read_csv(sample_mesh_file_path, encoding='shift-jis')

# Rename column `id` to `mesh_id`
sample_mesh_data.rename(columns={'id': 'mesh_id'}, inplace=True)

# Rename Japanese column to English
sample_mesh_data.rename(columns={'平均頻度(1年平均降雹回数)': 'average_hail_frequency_per_year'}, inplace=True)

# Merge necessary columns
merged_data = pd.merge(solar_panel_data, sample_mesh_data[['mesh_id', 'average_hail_frequency_per_year']], on='mesh_id', how='left')

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Save result with UTF-8-SIG encoding (prevents Excel from garbling characters)
merged_data.to_csv(output_file_path, index=False, encoding='utf-8-sig')

print(f"Processing complete. The file has been saved at: {output_file_path}")
