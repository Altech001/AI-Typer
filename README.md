<div align="center">
  <img src="https://raw.githubusercontent.com/simonong4/AI-Typer-Agent/main/docs/logo.png" alt="AI Typer Agent Logo" width="200"/>
  <h1>AI Typer Agent</h1>
</div>

<p align="center">
  Intelligent Typing Automation with Pydantic-AI
</p>

<div align="center">
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Platform-Ubuntu%20%7C%20Windows-blue.svg" alt="Platform">
  </a>
  <a href="https://www.python.org/downloads/release/python-370/">
    <img src="https://img.shields.io/badge/Python-3.7+-brightgreen.svg" alt="Python">
  </a>
   <a href="https://github.com/simonong4/AI-Typer-Agent/issues">
    <img src="https://img.shields.io/badge/Contribute-Issues-red.svg" alt="Contribute">
  </a>
   <a href="https://github.com/simonong4/AI-Typer-Agent/pulls">
    <img src="https://img.shields.io/badge/Contribute-Pull%20Request-green.svg" alt="Contribute">
  </a>
</div>

<br>

AI Typer Agent is an intelligent automation tool designed to streamline typing tasks across both Ubuntu and Windows platforms. Utilizing the pydantic-ai framework, it offers a blend of AI-driven efficiency and user-friendly interfaces, with Streamlit for Ubuntu and CustomTkinter for Windows.

## ✨ Features

*   **Cross-Platform Compatibility**: Seamless operation on Ubuntu and Windows.
*   **AI-Enhanced Automation**: Leverages the power of pydantic-ai for intelligent typing.
*   **Intuitive Web UI (Ubuntu)**: Streamlit-based interface for effortless control.
*   **Native Desktop UI (Windows)**: CustomTkinter provides a responsive native experience.
*   **Robust Browser Automation**: Built on Playwright for reliable browser interactions.

## 🛠️ Technologies Used

*   [Python](https://www.python.org/)
*   [pydantic-ai](https://pydantic.ai/)
*   [Playwright](https://playwright.dev/)
*   [Streamlit](https://streamlit.io/)
*   [CustomTkinter](https://customtkinter.tomschimansky.com/)

## 🚀 Installation

### Prerequisites

*   Python 3.7+
*   pip

### 💻 Ubuntu (Streamlit UI)

1.  Clone the repository:
    ```bash
    git clone https://github.com/simonong4/AI-Typer-Agent.git
    cd AI-Typer-Agent
    ```

2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Install Playwright browsers:
    ```bash
    playwright install
    ```

5.  Run the Streamlit app:
    ```bash
    streamlit run app.py
    ```

### 🖥️ Windows (CustomTkinter UI)

1.  Clone the repository:
    ```bash
    git clone https://github.com/simonong4/AI-Typer-Agent.git
    cd AI-Typer-Agent
    ```

2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Install Playwright browsers:
    ```bash
    playwright install
    ```

5.  Run the CustomTkinter app:
    ```bash
    python windows_app.py
    ```

## ⚙️ Configuration

Create a `.env` file in the root directory with the following variables:

```
API_KEY=your_api_key
BROWSER=chromium
```

## 🤝 Contributing

We welcome contributions to the AI Typer Agent project! To contribute:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Implement your changes.
4.  Test your changes thoroughly.
5.  Submit a pull request with a clear description of your changes.

Please follow our [Code of Conduct](link_to_code_of_conduct) when contributing to this project.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

*   [pydantic-ai](https://pydantic.ai/) - For providing the AI framework.
*   [Playwright](https://playwright.dev/) - For enabling reliable browser automation.
*   [Streamlit](https://streamlit.io/) - For simplifying the creation of the web UI.
*   [CustomTkinter](https://customtkinter.tomschimansky.com/) - For providing the customizable Tkinter widgets for the Windows UI.

## 📧 Contact

*   Email: your_email@example.com
*   Website: [https://luco.com](https://luco.com)
