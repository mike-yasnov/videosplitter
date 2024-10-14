import subprocess
import os

def main():
    # Указываем путь к вашему Streamlit-приложению
    script_path = os.path.join(os.path.dirname(__file__), 'split_videos.py')
    subprocess.run(["streamlit", "run", script_path])

if __name__ == "__main__":
    main()
