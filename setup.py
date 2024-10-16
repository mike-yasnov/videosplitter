from setuptools import setup, find_packages

setup(
    name="videosplitter",
    version="1.1.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "streamlit",
        "opencv-python",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "videosplitter = videosplitter.__main__:main",
        ],
    },
)
