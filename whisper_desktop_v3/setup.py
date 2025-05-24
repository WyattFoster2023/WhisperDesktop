from setuptools import setup, find_packages

setup(
    name="whisper_desktop",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6",
        "pyqtgraph",
        "numpy",
        "pyaudio",
        "openai-whisper",
        "pyautogui",
    ],
    entry_points={
        "console_scripts": [
            "whisper-desktop=whisper_desktop.run:run_gui",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A standalone transcription application using OpenAI's Whisper model",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/whisper_desktop",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
) 