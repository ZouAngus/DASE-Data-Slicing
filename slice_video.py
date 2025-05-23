import cv2
import os
import pandas as pd

# --- CONFIGURATION ---
video_code = '01'
video_suffix = 'C'
video_base_path = "/home/angus/cv_slice_data/mocap_data/raw_video/25.1.20_01"       # Path to your video file
excel_path = f'/home/angus/cv_slice_data/excel/DataCollection_{video_code}.xlsx'        # Path to your Excel file
sheet_video_map = {
    'Gaming Museum':   f'{video_code}_museum_{video_suffix}.mp4',
    'BowlingVR':       f'{video_code}_bowling_{video_suffix}.mp4',
    'Gallery of H.K. History': f'{video_code}_gallery_{video_suffix}.mp4',
    'Hong Kong Time Travel':   f'{video_code}_travel_{video_suffix}.mp4',
    'Boss Fight':      f'{video_code}_boss_{video_suffix}.mp4',
    'Candy Shooter':   f'{video_code}_candy_{video_suffix}.mp4'
}
video_format = 'mp4'                     # File format
output_path = f'./output/videos/'  # Folder where sliced CSV files will be saved

# --- SETUP ---
for sheet_name, video_file in sheet_video_map.items():
    video_path = os.path.join(video_base_path, video_file)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error: Could not open video.")
        exit()

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use 'XVID' for .avi if needed

    output_folder = os.path.join(output_path, f"{video_file[:-4]}")
    os.makedirs(output_folder, exist_ok=True)
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    # --- forward‐fill Action names so each row gets its corresponding action ---
    df['action_ff'] = df['Action'].ffill()

    rep_start_cols = [col for col in df.columns if 'Repetition' in col and 'Start' in col]
    rep_end_cols = [col for col in df.columns if 'Repetition' in col and 'End' in col]
    rep_nums = set()
    for col in rep_start_cols + rep_end_cols:
        try:
            rep_num = int(col.split()[1])
            rep_nums.add(rep_num)
        except:
            continue
    num_repetitions = max(rep_nums) if rep_nums else 0
    print(f"[{sheet_name}] max repetitions = {num_repetitions}")

    for row_idx, row in df.iterrows():
        for rep in range(1, num_repetitions + 1):
            start_col = f"Repetition {rep} Start"
            end_col   = f"Repetition {rep} End"

            start = row.get(start_col)
            end   = row.get(end_col)

            if pd.notna(start) and pd.notna(end):
                start_frame = int(start)
                end_frame   = int(end)
                # parse video_file name to extract code, name, suffix
                root, _ = os.path.splitext(video_file)
                vid_code, vid_name, vid_suffix = root.split('_')
                # grab and sanitize action name for this row
                action     = df.loc[row_idx, 'action_ff']
                action_s   = str(action).replace(' ', '-').lower()
                # build new clip filename
                clip_filename = os.path.join(
                    output_folder,
                    f"{vid_code}_{vid_name}_{vid_suffix}_"
                    f"{action_s}_row{row_idx+1}_rep{rep}.mp4"
                )

                out = cv2.VideoWriter(clip_filename, fourcc, fps, (width, height))
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

                for i in range(start_frame, end_frame + 1):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)

                out.release()
                print(f"Saved: {clip_filename}")
            else:
                print(f"Skipped: row {row_idx+1}, repetition {rep} (missing data)")

    cap.release()
print("All available clips saved.")
