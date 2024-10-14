from setuptools import setup, find_packages

setup(
    name="videosplitter",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "streamlit",
        "opencv-python",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "videosplitter = split_videos:main",
        ],
    },
)
