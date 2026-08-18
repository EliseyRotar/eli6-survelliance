# Contributing to ELI6 Surveillance

Thank you for your interest in contributing! Here's how to get started.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/eli6-survelliance.git
   cd eli6-survelliance
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Copy the example config:
   ```bash
   cp camera_config.example.json camera_config.json
   ```
5. Edit `camera_config.json` with your own camera URLs.

## Development

- Main application: `src/webcams.py`
- Web templates: `templates/`
- Static assets: `static/`
- Utility scripts: `src/`
- Camera testing tools: `camera_testing/`

## Submitting Changes

1. Create a new branch: `git checkout -b feature/your-feature`
2. Make your changes with clear, focused commits
3. Test your changes: `python3 camera_testing/test_camera_urls.py`
4. Push and open a Pull Request

## Code Style

- Follow PEP 8 for Python code
- Add docstrings to functions and classes
- Keep commits focused — one logical change per commit

## Reporting Issues

Open a GitHub issue with:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
