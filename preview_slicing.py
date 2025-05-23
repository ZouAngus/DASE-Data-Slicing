import os, json
import cv2
import numpy as np
import pandas as pd
import re

# --- CONFIGURATION: point these to your folders + camera JSON ---
csv_folder    = "/home/angus/cv_slice_data/output/csv/01_boss_C"
video_folder  = "/home/angus/cv_slice_data/output/videos/01_boss_C"   # now a folder of clip_*.mp4 files
camera_json   = "/home/angus/cv_slice_data/camera_data/extrinsics_middle.json"
output_folder = "/home/angus/cv_slice_data/output/previews"

os.makedirs(output_folder, exist_ok=True)

# load camera intrinsics+extrinsics
with open(camera_json, 'r') as f:
    cam = json.load(f)
K   = np.array(cam['camera_matrix'])       # 3×3
P4  = np.array(cam['best_extrinsic'])      # 3×4
proj = K.dot(P4)                           # full 3×4 projection
print(f"[INFO] Loaded camera, proj matrix shape = {proj.shape}")

# build a map of (row,rep) → video file using new clip_ naming
video_map = {}
for vid in sorted(os.listdir(video_folder)):
    if not vid.lower().endswith(".mp4"):
        continue
    # match any filename ending in _row{row}_rep{rep}.mp4
    m = re.match(r".*_row([0-9]+)_rep([0-9]+)\.mp4$", vid)
    if m:
        key = (m.group(1), m.group(2))
        video_map[key] = os.path.join(video_folder, vid)
    else:
        print(f"[WARN] skipping unrecognized video name: {vid}")

for csv_name in sorted(os.listdir(csv_folder)):
    if not csv_name.lower().endswith(".csv"):
        continue

    # parse slice CSV name: slice_{code}_{name}_{suffix}_{action}_row{row}_rep{rep}.csv
    m = re.match(
        r"([^_]+)_([^_]+)_([^_]+)_(.+?)_row([0-9]+)_rep([0-9]+)\.csv$",
        csv_name
    )
    if not m:
        print(f"[WARN] skipping unrecognized csv name: {csv_name}")
        continue
    code, vid_name, suffix, action, row_i, rep = m.groups()
    csv_path = os.path.join(csv_folder, csv_name)

    # lookup matching video by (row,rep)
    video_path = video_map.get((row_i, rep))
    if not video_path:
        print(f"[WARN] no clip for row{row_i}_rep{rep}, skipping")
        continue

    # build preview filename with code, video name, suffix, action, row & rep
    action_safe = action.replace(' ', '-')
    preview_name = (
        f"preview_{code}_{vid_name}_{suffix}_"
        f"{action_safe}_row{row_i}_rep{rep}.mp4"
    )
    out_path = os.path.join(output_folder, preview_name)

    print(f"[INFO] Processing pair: {csv_name} ⟷ {os.path.basename(video_path)}")

    # load CSV slice
    df3d = pd.read_csv(csv_path)
    print(f"       CSV rows = {len(df3d)}, columns = {len(df3d.columns)}")

    # open video clip
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    W   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_path, fourcc, fps, (W, H))
    print(f"       Video opened: {W}×{H}@{fps:.1f}fps → writing {out_path}")

    # project & write each frame
    for i, row in df3d.iterrows():
        ret, img = cap.read()
        if not ret:
            print("       [WARN] video ended prematurely")
            break

        # detect joint columns like '0_x','0_y','0_z',…
        joint_cols = [c for c in df3d.columns if "_" in c]
        if joint_cols:
            jids = sorted({c.split("_")[0] for c in joint_cols},
                          key=lambda s: int(s))
            for jid in jids:
                X3d = np.array([
                    row[f"{jid}_x"],
                    row[f"{jid}_y"],
                    row[f"{jid}_z"],
                    1.0
                ])
                x2d = proj.dot(X3d)
                if not np.isfinite(x2d).all() or x2d[2] == 0:
                    continue
                u, v = int(x2d[0]/x2d[2]), int(x2d[1]/x2d[2])
                cv2.circle(img, (u, v), 5, (0,0,255), -1)
        else:
            # fallback single‐point case
            row = row.rename(lambda s: s.strip().lower())
            X3d = np.array([row['x'], row['y'], row['z'], 1.0])
            x2d = proj.dot(X3d)
            if np.isfinite(x2d).all() and x2d[2] != 0:
                u, v = int(x2d[0]/x2d[2]), int(x2d[1]/x2d[2])
                cv2.circle(img, (u, v), 5, (0,0,255), -1)

        # frame counter
        cv2.putText(img, f"frame {i+1}/{len(df3d)}",
                    (10, H-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

        out.write(img)

    cap.release()
    out.release()
    print(f"[OK] Saved preview: {out_path}\n")