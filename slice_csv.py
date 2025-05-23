import pandas as pd
import os

# --- CONFIGURATION ---
video_code = '13'
video_suffix = 'C' ### different angle have different offset, so we need to slice them separately
video_folder_name = "25.1.17_13"

excel_path = f"/data/sda1/cv_slice_data/excel/DataCollection_{video_code}.xlsx"  # Path to the Excel file with cutting points
offset_excel_path = '/data/sda1/cv_slice_data/new_csv_offset.xlsx'  # Path to the new Excel file with offsets
csv_folder_path = f"/data/sda1/cv_slice_data/extracted_csv/{video_folder_name}"  # Folder where CSV files for each video are stored
output_path = '/data/sda1/cv_slice_data/output/csv'  # Folder where sliced CSV files will be saved


sheet_csv_map = {
    'Gaming Museum':   f'{video_code}_museum_{video_suffix}_3d.csv',
    'BowlingVR':       f'{video_code}_bowling_{video_suffix}_3d.csv',
    'Gallery of H.K. History': f'{video_code}_gallery_{video_suffix}_3d.csv',
    'Hong Kong Time Travel':   f'{video_code}_travel_{video_suffix}_3d.csv',
    'Boss Fight':      f'{video_code}_boss_{video_suffix}_3d.csv',
    'Candy Shooter':   f'{video_code}_candy_{video_suffix}_3d.csv',
}

# Path to your Excel file with cutting points
sheet_video_map = {
    'Gaming Museum':   f'{video_code}_museum_{video_suffix}.mp4',
    'BowlingVR':       f'{video_code}_bowling_{video_suffix}.mp4',
    'Gallery of H.K. History': f'{video_code}_gallery_{video_suffix}.mp4',
    'Hong Kong Time Travel':   f'{video_code}_travel_{video_suffix}.mp4',
    'Boss Fight':      f'{video_code}_boss_{video_suffix}.mp4',
    'Candy Shooter':   f'{video_code}_candy_{video_suffix}.mp4'
}

# --- Function to Slice CSV Based on Frame Ranges and Offsets ---
def slice_csv_based_on_offsets(csv_path, sheet_name, csv_name, data_collection_path, output_path, offset_df=None):
     
    # --- read or default the offset data for the current sheet ---
    video_name = sheet_video_map[sheet_name]
    if offset_df is None:
        offset_value = 0
    else:
        matched_row = offset_df[offset_df['video_name'] == video_name]
        if matched_row.empty:
            print(f"No offset data found for {video_name}. Skipping...")
            return
        offset_value = matched_row['offset'].values[0]  # Get the offset value for this video

    # --- Extract relevant frame range information from the Data Collection Excel ---
    df = pd.read_excel(data_collection_path, sheet_name=sheet_name)
    # --- forward‐fill Action names so each row gets its corresponding action ---
    df['action_ff'] = df['Action'].ffill()

    rep_start_cols = [col for col in df.columns if 'Repetition' in col and 'Start' in col]
    rep_end_cols = [col for col in df.columns if 'Repetition' in col and 'End' in col]

    # Read the extracted 3D points CSV
    csv_data = pd.read_csv(csv_path)
    
    output_folder = os.path.join(output_path, f"{csv_name[:-7]}")
    os.makedirs(output_folder, exist_ok=True)

    # --- Iterate over each repetition and slice the CSV accordingly ---
    for row_idx, row in df.iterrows():
        for rep in range(1, len(rep_start_cols)+1):
            start = row.get(f"Repetition {rep} Start")
            end   = row.get(f"Repetition {rep} End")

            if pd.notna(start) and pd.notna(end):
                s = int(start) + offset_value
                e = int(end) + offset_value
                slice_df = csv_data.iloc[s:e].reset_index(drop=True)
                # parse video_name to extract code, name, suffix
                root = os.path.splitext(video_name)[0]
                vid_code, vid_name, vid_suffix = root.split('_')
                # grab and sanitize action name: use hyphens for multi-word
                action = df.loc[row_idx, 'action_ff']
                action_h = str(action).strip().replace(' ', '-').lower()
                # build new slice CSV filename
                out_name = (
                    f"{vid_code}_{vid_name}_{vid_suffix}_"
                    f"{action_h}_row{row_idx+1}_rep{rep}.csv"
                )
                slice_df.to_csv(os.path.join(output_folder, out_name), index=False)
                print(f"Sliced CSV saved: {os.path.join(output_folder, out_name)}")


# --- Load the Offset Excel and Data Collection Excel ---
offset_df = pd.read_excel(offset_excel_path, sheet_name=video_folder_name)

# --- Iterate over each sheet and process the corresponding CSV file ---
for sheet_name, csv_name in sheet_csv_map.items():
    csv_path = os.path.join(csv_folder_path, csv_name)
    slice_csv_based_on_offsets(csv_path,
                               sheet_name,
                               csv_name,
                               excel_path,
                               output_path,
                               offset_df,
                               )
