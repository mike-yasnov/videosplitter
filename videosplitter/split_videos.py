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
import concurrent.futures
import logging

import rich
from rich.tree import Tree
from rich.console import Console

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def split_video_by_timecodes(video_path, timecodes, step, codec='mp4v', quality=95):
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    
    video_name = Path(video_path).stem
    output_dir = Path("output") / re.sub(r'[:"<>|?*]', '_', video_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_parts = len(timecodes)

    for i, (start, end) in enumerate(timecodes):
        start_frame = int(start.total_seconds() * fps)
        end_frame = int(end.total_seconds() * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        output_filename = output_dir / f"{video_name}_part_{i+1}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(str(output_filename), fourcc, fps, (
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ))
        
        frame_output_dir = output_dir / re.sub(r'[:"<>|?*]', '_', f"frames_part_{i+1}")
        frame_output_dir.mkdir(parents=True, exist_ok=True)
        
        for frame_num in range(start_frame, end_frame, step):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            frame_filename = frame_output_dir / f"frame_{frame_num}.jpg"
            cv2.imwrite(str(frame_filename), frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        out.release()
        
        progress = int(((i + 1) / total_parts) * 100)
        progress_bar.progress(progress)
        status_text.text(f"Обработка части {i + 1} из {total_parts}...")
    
    progress_bar.progress(100)
    status_text.text("Обработка завершена!")
    cap.release()

def zip_output_folder(video_name):
    output_dir = Path("output") / video_name
    zip_filename = Path("output") / (re.sub(r'[:"<>|?*]', '_', video_name) + ".zip")
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
    
    return console.export_text()

def select_folder():
    root_path = Path.home()
    current_path = st.sidebar.text_input("Введите путь к папке с видео:", value=str(root_path))
    current_path_obj = Path(current_path)
    if current_path_obj.exists() and current_path_obj.is_dir():
        folder_tree = render_directory_tree(current_path_obj)
        st.sidebar.text(folder_tree)
        return current_path
    else:
        st.sidebar.error("Неверный путь. Пожалуйста, введите правильный путь к папке.")
        return None

# Streamlit App Customization
st.set_page_config(page_title="Разделитель видео", page_icon=":scissors:", layout="wide")

# Streamlit App
st.title("🎥 Разделитель видео по таймкодам")

# Folder input using a text input in the sidebar
selected_folder = select_folder()

if selected_folder:
    input_folder = selected_folder
    input_path = Path(input_folder)
    if not input_path.exists() or not input_path.is_dir():
        st.error("Неверный путь к папке.")
    else:
        video_files = list(input_path.glob("*.mp4")) + list(input_path.glob("*.avi")) + list(input_path.glob("*.mov")) + list(input_path.glob("*.mkv"))
        if not video_files:
            st.warning("В указанной папке не найдено поддерживаемых видеофайлов (.mp4, .avi, .mov, .mkv).")
        else:
            for video_file in video_files:
                timecodes_str = st.text_input(f"Введите таймкоды для {video_file.name} (например, 00:43-00:52, 01:31-02:09):", key=f"timecodes_{video_file.stem}")
                step = st.number_input(f"Введите шаг для сохранения кадров для {video_file.name} (например, 1 для каждого кадра, 2 для каждого второго кадра):", min_value=1, value=1, key=f"step_{video_file.stem}")
                quality = st.slider(f"Выберите качество выходных кадров для {video_file.name} (1-100):", min_value=1, max_value=100, value=95, key=f"quality_{video_file.stem}")
                codec = st.selectbox(f"Выберите кодек для {video_file.name}:", ["mp4v", "XVID", "MJPG", "X264"], key=f"codec_{video_file.stem}")
                if timecodes_str and f'processing_{video_file.stem}' not in st.session_state:
                    timecodes = parse_timecodes(timecodes_str)
                    split_video_by_timecodes(video_file, timecodes, step, codec, quality)
                    zip_file = zip_output_folder(re.sub(r'[:"<>|?*]', '_', video_file.stem)) if Path(f'output/{video_file.stem}').exists() else None
                    st.session_state[f'processing_{video_file.stem}'] = True
                    st.success(f"Обработка завершена для {video_file.name}")
                    if zip_file:
                        st.download_button(
                            label="📥 Скачать ZIP-файл",
                            data=open(zip_file, "rb").read(),
                            file_name=zip_file.name,
                            mime="application/zip",
                            key=f"download_{video_file.stem}"
                        )