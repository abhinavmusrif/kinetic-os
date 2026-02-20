![License](https://img.shields.io/github/license/abhinavmusrif/kinetic-os)

![Stars](https://img.shields.io/github/stars/abhinavmusrif/kinetic-os)

![Issues](https://img.shields.io/github/issues/abhinavmusrif/kinetic-os)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)

# Kinetic-OS: The Human-Kinetic Autonomous Operator

**Kinetic-OS** is a high-performance, memory-first autonomous operator platform designed for native Windows environments. It enables AI agents to "see" and "act" at human speed by bypassing slow vision-only loops in favor of a proprietary **Spatial UI Mapping** engine.

## 🚀 The Competitive Edge

* **⚡ Sub-100ms Perception**: Uses the **Windows Accessibility Tree** (UIAutomation) to map screen elements instantly—orders of magnitude faster than traditional OCR/VLM methods.
* **🖱️ Human-Kinetic Inputs**: Features a custom input controller using **Bezier curves**, ease-in/out acceleration, and micro-hesitations to bypass anti-bot detection.
* **🛡️ Focus-Verified Execution**: Strictly verifies window focus and active app state before any action, preventing "blind" execution or accidental clicks.
* **🧠 Cognitive Memory Pipeline**: A bio-inspired 7-layer memory architecture (Episodic, Semantic, Procedural, etc.) for long-term learning and habit formation.
* **🔄 Self-Correcting Loop**: A continuous `Plan → Act → Observe → Evaluate` loop that allows the agent to detect failures and autonomously adapt its strategy.

## 🏗️ System Architecture

1.  **Perception Engine**: Real-time UI tree parsing with Gemini/Groq VLM and Tesseract OCR fallbacks.
2.  **Cognitive Brain**: Multi-provider support (Gemini 2.0 Flash, Groq, OpenAI) with exponential backoff and agentic throttling.
3.  **Kinetic Controller**: Native OS interaction layer for Windows with human-like kinematics.
4.  **Memory Consolidator**: An offline "Dream Cycle" that builds long-term internal models and resolves belief contradictions.

## 🛡️ Safe Mode (Default)

Policies are defined in `config/permissions.yaml`. By default:
* `allow_shell: false`
* `allow_file_write_outside_workspace: false`
* `allow_os_automation: false`
* `allow_network: false`
* Confirmation required for all sensitive actions

## 📦 Install

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 🚦 Quickstart

### 1. Configure API
Copy the example environment file and add your `GEMINI_API_KEY`.
```bash
cp .env.example .env
# Open .env and paste your Gemini API key from Google AI Studio
```

### 2. Run a Goal
Launch the agent and watch it navigate the OS and browser.
```bash
ao run-goal "Open the web browser, go to wikipedia.org, and search for 'Robotics'"
```

### 3. Inspect Memory
View what the agent learned and how it structured the task.
```bash
ao memory inspect
```

## 🎥 OS Automation Demos (Windows Only)

Ensure `AO_ENABLE_UI_TESTS="1"` is set to watch the agent take control:
* `python scripts/desktop_demos/demo_notepad_task.py`: Automated human-like typing.
* `python scripts/desktop_demos/demo_browser_task.py`: Browser verification and navigation.
* `python scripts/desktop_demos/demo_vscode_task.py`: VSCode terminal management.

## 📄 License
This project is licensed under the **MIT License**.

## 🤝 Contributing
Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines on adding new tool integrations or LLM providers.
