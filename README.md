# Shark and Sharker

This project is a marketplace utility for Dark and Darker.

## Project Overview

The project consists of two core modules:

- **Shark**: The data gathering module
- **Sharker**: The data processing and machine learning (ML) module

## Installation

To install the project, follow these steps:

1. Clone the repository:
   ```sh
   git clone https://github.com/daburch/sharkandsharker.git
   ```
2. Navigate to the project directory:
   ```sh
   cd sharkandsharker
   ```
3. _(Optional)_ Create a virtual environment:
   ```sh
   python -m venv venv
   ```
   Activate the virtual environment:
   - On Windows:
     ```sh
     .\venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```sh
     source venv/bin/activate
     ```
4. Install the required dependencies:
   ```sh
   python -m pip install -r requirements.txt
   ```
5. Set up the environment variables as needed.

## Usage

```sh
python src/main.py --mode predict
```
