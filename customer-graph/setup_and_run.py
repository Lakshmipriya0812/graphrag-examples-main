#!/usr/bin/env python3
"""
Setup and run script for the customer graph unstructured ingest
This script handles the directory change and dependency installation
"""

import os
import sys
import subprocess
import importlib

def install_package(package):
    """Install a package if it's not already installed"""
    try:
        importlib.import_module(package)
        print(f"✓ {package} is already installed")
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ {package} installed successfully")

def main():
    # Change to the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"Changed to directory: {os.getcwd()}")
    
    # Install required packages
    required_packages = [
        "python-dotenv",
        "langchain-community",
        "langchain-text-splitters",
        "neo4j",
        "sentence-transformers",
        "torch",
        "transformers"
    ]
    
    print("Checking and installing required packages...")
    for package in required_packages:
        install_package(package)
    
    # Try to install ollama if needed
    try:
        importlib.import_module("ollama")
        print("✓ ollama is already installed")
    except ImportError:
        print("Note: ollama is not installed. The script will use a mock LLM instead.")
        print("To install ollama: pip install ollama")
    
    print("\n" + "="*50)
    print("Running unstructured_ingest.py...")
    print("="*50)
    
    # Run the main script
    try:
        exec(open("unstructured_ingest.py").read())
        print("\n✓ Script completed successfully!")
    except Exception as e:
        print(f"\n✗ Error running script: {e}")
        print("Please check your Neo4j connection and environment variables.")

if __name__ == "__main__":
    main() 