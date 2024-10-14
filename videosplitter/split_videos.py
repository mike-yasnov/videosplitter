import os
import re
import zipfile
import cv2
import streamlit as st
from pathlib import Path
from datetime import timedelta
import streamlit.components.v1 as components
import threading
import platform
import time

import rich
from rich.tree import Tree
from rich.console import Console

def parse_timecodes(timecodes_str):
    pattern = r"(\d{2}:\d{2}-\d{2}:\d{2})"
    matches = re.findall(pattern, timecodes_str)
    timecodes = []
    for match in matches:
        start_str, end_str = match.split('-')
        start = timedelta(minutes=int(start_str.split(':')[0]), seconds=int(start_str.split(':')[1]))
        end = timedelta(minutes=int(end_str.split(':')[0]), seconds=int(end_str.split(':')[1]))
        timecodes.append((start, end))
    return timecodes

def split_video_by_timecodes(video_path, timecodes, step):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    
    video_name = Path(video_path).stem
    output_dir = Path("output") / video_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_parts = len(timecodes)

    for i, (start, end) in enumerate(timecodes):
        start_frame = int(start.total_seconds() * fps)
        end_frame = int(end.total_seconds() * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        output_filename = output_dir / f"{video_name}_part_{i+1}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_filename), fourcc, fps, (
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ))
        
        frame_output_dir = output_dir / f"frames_part_{i+1}"
        frame_output_dir.mkdir(parents=True, exist_ok=True)
        
        for frame_num in range(start_frame, end_frame, step):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            frame_filename = frame_output_dir / f"frame_{frame_num}.jpg"
            cv2.imwrite(str(frame_filename), frame)
        out.release()
        
        progress = int(((i + 1) / total_parts) * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing part {i + 1} of {total_parts}...")
    
    progress_bar.progress(100)
    status_text.text("Processing complete!")
    cap.release()

def zip_output_folder(video_name):
    output_dir = Path("output") / video_name
    zip_filename = Path("output") / f"{video_name}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)
    return zip_filename

def render_directory_tree(path):
    tree = Tree(f"[bold blue]{path}[/bold blue]")
    for item in path.iterdir():
        if item.name.startswith('.') or not os.access(item, os.R_OK):
            continue
        if item.is_dir():
            tree.add(f"📁 {item.name}")
    console = Console(record=True)
    console.print(tree)
    return console.export_text()

def select_folder():
    root_path = Path.home()
    current_path = st.sidebar.text_input("Enter the path to the folder containing videos:", value=str(root_path))
    current_path_obj = Path(current_path)
    if current_path_obj.exists() and current_path_obj.is_dir():
        folder_tree = render_directory_tree(current_path_obj)
        st.sidebar.text(folder_tree)
        return current_path
    else:
        st.sidebar.error("Invalid path. Please enter a valid directory path.")
        return None

# Streamlit App
st.title("Video Splitter by Timecodes")

# Folder input using a text input in the sidebar
selected_folder = select_folder()

if selected_folder:
    input_folder = selected_folder
    input_path = Path(input_folder)
    if not input_path.exists() or not input_path.is_dir():
        st.error("Invalid folder path.")
    else:
        video_files = list(input_path.glob("*.mp4")) + list(input_path.glob("*.avi")) + list(input_path.glob("*.mov")) + list(input_path.glob("*.mkv"))
        if not video_files:
            st.warning("No supported video files (.mp4, .avi, .mov, .mkv) found in the specified folder.")
        else:
            for video_file in video_files:
                st.header(f"Processing {video_file.name}")
                timecodes_str = st.text_input(f"Enter timecodes for {video_file.name} (e.g., 00:43-00:52, 01:31-02:09):")
                step = st.number_input(f"Enter step for saving frames for {video_file.name} (e.g., 1 for every frame, 2 for every second frame):", min_value=1, value=1)
                if timecodes_str:
                    timecodes = parse_timecodes(timecodes_str)
                    if 'processing_done' not in st.session_state:
                        split_video_by_timecodes(video_file, timecodes, step)
                        st.session_state['processing_done'] = True
                    zip_file = zip_output_folder(video_file.stem)
                    st.success(f"Finished processing {video_file.name}")
                    st.download_button(
                        label="Download ZIP file",
                        data=open(zip_file, "rb").read(),
                        file_name=zip_file.name,
                        mime="application/zip"
                    )

# To run the app with a simple command
def main():
    import subprocess
    import sys
    command = [sys.executable, "-m", "streamlit", "run", "videosplitter/split_videos.py"]
    subprocess.run(command)

if __name__ == "__main__":
    main()

