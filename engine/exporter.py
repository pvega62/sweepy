import os
import csv
import json
import pandas as pd

def export_to_csv(jobs: list, output_path: str):
    """
    Export the job list to a CSV file using pandas.
    """
    if not jobs:
        print("No jobs to export to CSV.")
        return
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df = pd.DataFrame(jobs)
    
    # Reorder columns to put the most important ones first
    cols = df.columns.tolist()
    priority_cols = ['title', 'company', 'location', 'match_score', 'badge', 'url']
    
    final_cols = [c for c in priority_cols if c in cols]
    final_cols += [c for c in cols if c not in priority_cols]
    
    df = df[final_cols]
    
    try:
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"CSV successfully generated at: {output_path}")
    except Exception as e:
        print(f"Error exporting to CSV: {e}")

def export_to_json(jobs: list, output_path: str):
    """
    Export the job list to a JSON file.
    """
    if not jobs:
        print("No jobs to export to JSON.")
        return
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=4, ensure_ascii=False)
        print(f"JSON successfully generated at: {output_path}")
    except Exception as e:
        print(f"Error exporting to JSON: {e}")
