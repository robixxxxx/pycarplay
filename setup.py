"""
PyCarPlay - CarPlay Integration Module for PyQt Applications

Based on react-carplay (https://github.com/rhysmorgan134/react-carplay) by Rhys Morgan.
Adapted for Python/Qt with enhanced flexibility and protocol-agnostic design.
"""
from setuptools import setup, find_packages
import os

# Read README for long description
def read_file(filename):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

setup(
    name='pycarplay-qt',
    version='0.1.0',
    author='Robert Burda',
    description='CarPlay integration module for PyQt6 applications with customizable UI',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    url='https://github.com/robixxxxx/pycarplay',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    package_data={
        'pycarplay': [
            'ui/default/*.qml',
            'ui/components/*.qml',
        ],
    },
    include_package_data=True,
    install_requires=[
        'PySide6>=6.4.0',
        'pyusb>=1.2.1',
        'opencv-python>=4.8.0',
        'numpy>=1.24.0',
        'pyaudio>=0.2.13',
        'cryptography>=41.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
        ],
    },
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Multimedia :: Video',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
    ],
    keywords='carplay, pyqt6, automotive, qt, multimedia, video',
    project_urls={
        'Bug Reports': 'https://github.com/robixxxxx/pycarplay/issues',
        'Source': 'https://github.com/robixxxxx/pycarplay',
    },
)
