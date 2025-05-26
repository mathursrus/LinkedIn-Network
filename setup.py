from setuptools import setup, find_packages

setup(
    name="linkedin-network-builder",
    version="1.0.0",
    description="A local API server for exploring LinkedIn networks",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "playwright>=1.20.0",
        "asyncio-compat>=0.1.2",
    ],
    entry_points={
        "console_scripts": [
            "linkedin-network=main:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 