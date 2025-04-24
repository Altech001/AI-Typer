import os
import re
import tempfile
import logging
import asyncio
import threading
from pathlib import Path
import time
from tkinter import filedialog, StringVar, BooleanVar, DoubleVar, IntVar
import customtkinter as ctk
from pynput.mouse import Controller as MouseController
from PIL import Image, ImageTk

# Import your existing utilities
from utils import (
    extract_file_content,
    is_valid_doc,
    display_screenshots,
)
from typer import DocumentRetyper, extract_text_from_docx
from validation import display_error_details
from analzyer import analyze_docx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set appearance mode and default color theme
ctk.set_appearance_mode("Dark")  # Black-and-white theme
ctk.set_default_color_theme("dark-blue")  # Minimal color usage

class CustomDialog(ctk.CTkToplevel):
    """Custom dialog to replace CTkMessagebox, avoiding grab failed error."""
    def __init__(self, parent, title="Dialog", message="", icon="info", option_1="OK"):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x200")
        self.resizable(False, False)
        self.transient(parent)
        
        # Ensure dialog is viewable before grabbing focus
        self.update_idletasks()
        self.wait_visibility()
        self.grab_set()

        # Center dialog
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 100
        self.geometry(f"+{x}+{y}")

        frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1C2526")
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        icon_label = ctk.CTkLabel(
            frame,
            text="ℹ️" if icon == "info" else "✅" if icon == "check" else "❌",
            font=ctk.CTkFont(size=24),
            text_color="white"
        )
        icon_label.pack(pady=(0, 10))

        message_label = ctk.CTkLabel(
            frame,
            text=message,
            wraplength=350,
            justify="center",
            text_color="white",
            font=ctk.CTkFont(size=12)
        )
        message_label.pack(pady=(0, 20))

        button = ctk.CTkButton(
            frame,
            text=option_1,
            command=self.destroy,
            fg_color="#4A4A4A",
            hover_color="#3A3A3A",
            text_color="white",
            corner_radius=10
        )
        button.pack()

class AITyper(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("VClass AI Typer")
        self.geometry("1100x700")
        self.minsize(500, 600)
        
        # App state
        self.processing_status = None
        self.result = None
        self.file_info = None
        self.screenshots = []
        self.uploaded_file_path = None
        self.file_content = None
        
        # Variables
        self.api_key_var = StringVar()
        self.reg_number_var = StringVar()
        self.password_var = StringVar()
        self.provider_var = StringVar(value="Google")
        self.model_var = StringVar(value="google-gla:gemini-2.0-flash")
        self.typing_speed_var = DoubleVar(value=0.03)
        self.chunk_size_var = IntVar(value=2000)
        self.headless_mode_var = BooleanVar(value=True)
        self.doc_type_var = StringVar(value="Docx / Word Document")
        self.screenshots_var = BooleanVar(value=True)
        self.contains_images_var = BooleanVar(value=True)
        self.error_correction_var = BooleanVar(value=True)
        
        # Create layout
        self.create_layout()
        
    def create_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Create top settings bar
        self.create_settings_bar()

        # Create main content area
        self.create_main_content()
    
    def create_settings_bar(self):
        """Create a responsive top settings bar."""
        settings_bar = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#1C2526")
        settings_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        settings_bar.grid_columnconfigure(7, weight=1)

        # Logo
        logo_label = ctk.CTkLabel(
            settings_bar,
            text="VClass AI Typer",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        logo_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # API Key
        api_frame = ctk.CTkFrame(settings_bar, fg_color="transparent")
        api_frame.grid(row=0, column=1, padx=5, pady=5)
        api_key_entry = ctk.CTkEntry(
            api_frame,
            width=100,
            placeholder_text="API Key",
            show="•",
            textvariable=self.api_key_var,
            corner_radius=6,
            fg_color="#2E2E2E",
            text_color="white"
        )
        api_key_entry.grid(row=0, column=0)

        # Model selection
        model_frame = ctk.CTkFrame(settings_bar, fg_color="transparent")
        model_frame.grid(row=0, column=2, padx=5, pady=5)
        model_options = [
            "google-gla:gemini-2.0-flash",
            "google-gla:gemini-1.5-flash",
            "mistral-small-latest",
            "groq:deepseek-r1-distill-llama-70b",
            "groq:gemma2-9b-it",
            "groq:llama3-8b-8192",
            "groq:mistral-saba-24b"
        ]
        model_menu = ctk.CTkOptionMenu(
            model_frame,
            values=model_options,
            variable=self.model_var,
            width=130,
            corner_radius=6,
            fg_color="#4A4A4A",
            button_color="#4A4A4A",
            button_hover_color="#3A3A3A",
            text_color="white"
        )
        model_menu.grid(row=0, column=0)

        # Typing Speed
        speed_frame = ctk.CTkFrame(settings_bar, fg_color="transparent")
        speed_frame.grid(row=0, column=3, padx=5, pady=5)
        speed_label = ctk.CTkLabel(
            speed_frame,
            text=f"{self.typing_speed_var.get():.3f}s",
            text_color="white",
            font=ctk.CTkFont(size=10)
        )
        speed_label.grid(row=0, column=0, padx=3)
        speed_slider = ctk.CTkSlider(
            speed_frame,
            from_=0.001,
            to=0.1,
            variable=self.typing_speed_var,
            width=70,
            command=lambda v: speed_label.configure(text=f"{float(v):.3f}s"),
            fg_color="#4A4A4A",
            progress_color="#FFFFFF",
            button_color="#FFFFFF"
        )
        speed_slider.grid(row=0, column=1)

        # Chunk Size
        chunk_frame = ctk.CTkFrame(settings_bar, fg_color="transparent")
        chunk_frame.grid(row=0, column=4, padx=5, pady=5)
        chunk_label = ctk.CTkLabel(
            chunk_frame,
            text=f"{self.chunk_size_var.get()}",
            text_color="white",
            font=ctk.CTkFont(size=10)
        )
        chunk_label.grid(row=0, column=0, padx=3)
        chunk_slider = ctk.CTkSlider(
            chunk_frame,
            from_=500,
            to=10000,
            variable=self.chunk_size_var,
            width=70,
            command=lambda v: chunk_label.configure(text=f"{int(v)}"),
            fg_color="#4A4A4A",
            progress_color="#FFFFFF",
            button_color="#FFFFFF"
        )
        chunk_slider.grid(row=0, column=1)

        # Switches
        switches_frame = ctk.CTkFrame(settings_bar, fg_color="transparent")
        switches_frame.grid(row=0, column=5, padx=5, pady=5)
        headless_switch = ctk.CTkSwitch(
            switches_frame,
            text="",
            variable=self.headless_mode_var,
            width=30,
            fg_color="#4A4A4A",
            progress_color="#FFFFFF"
        )
        headless_switch.grid(row=0, column=0, padx=2)
        screenshots_switch = ctk.CTkSwitch(
            switches_frame,
            text="",
            variable=self.screenshots_var,
            width=30,
            fg_color="#4A4A4A",
            progress_color="#FFFFFF"
        )
        screenshots_switch.grid(row=0, column=1, padx=2)
        error_correction_switch = ctk.CTkSwitch(
            switches_frame,
            text="",
            variable=self.error_correction_var,
            width=30,
            fg_color="#4A4A4A",
            progress_color="#FFFFFF"
        )
        error_correction_switch.grid(row=0, column=2, padx=2)

        # Reset button
        reset_button = ctk.CTkButton(
            settings_bar,
            text="Reset",
            command=self.reset_session,
            width=50,
            corner_radius=6,
            fg_color="#4A4A4A",
            hover_color="#3A3A3A",
            text_color="white"
        )
        reset_button.grid(row=0, column=6, padx=5, pady=5)

        # Theme switcher
        theme_menu = ctk.CTkOptionMenu(
            settings_bar,
            values=["Dark", "Light"],
            command=self.change_appearance_mode,
            width=70,
            corner_radius=6,
            fg_color="#4A4A4A",
            button_color="#4A4A4A",
            button_hover_color="#3A3A3A",
            text_color="white"
        )
        theme_menu.grid(row=0, column=7, padx=5, pady=5, sticky="e")

    def create_main_content(self):
        """Create the main content area with tabs."""
        content_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1C2526")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(content_frame, corner_radius=10, fg_color="#2E2E2E")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        header_label = ctk.CTkLabel(
            header_frame,
            text="VClass AI Typer",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        )
        header_label.grid(row=0, column=0, sticky="w", padx=20, pady=10)

        info_button = ctk.CTkButton(
            header_frame,
            text="ℹ️",
            width=30,
            height=30,
            corner_radius=15,
            command=self.show_info_dialog,
            fg_color="#4A4A4A",
            hover_color="#3A3A3A",
            text_color="white"
        )
        info_button.grid(row=0, column=1, sticky="e", padx=20, pady=10)

        # Tab view
        self.tabview = ctk.CTkTabview(
            content_frame,
            corner_radius=10,
            fg_color="#2E2E2E",
            segmented_button_fg_color="#4A4A4A",
            segmented_button_selected_color="#FFFFFF",
            segmented_button_selected_hover_color="#E0E0E0",
            text_color="white"
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Create tabs
        tab1 = self.tabview.add("Typer")
        tab2 = self.tabview.add("Automation")
        tab3 = self.tabview.add("Support")
        tab4 = self.tabview.add("Settings")

        # Configure tab grids
        for tab in [tab1, tab2, tab3, tab4]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(20, weight=1)

        # Set up each tab content
        self.setup_typer_tab(tab1)
        self.setup_automation_tab(tab2)
        self.setup_support_tab(tab3)
        self.setup_settings_tab(tab4)
        
    def setup_typer_tab(self, parent):
        """Setup the Typer tab content."""
        main_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#1C2526")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=2)
        main_frame.grid_rowconfigure(2, weight=1)

        # Left column: Controls
        left_frame = ctk.CTkFrame(main_frame, corner_radius=10, fg_color="#2E2E2E")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left_frame.grid_columnconfigure(0, weight=1)

        # Upload section
        upload_frame = ctk.CTkFrame(left_frame, corner_radius=10, fg_color="#2E2E2E")
        upload_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        upload_label = ctk.CTkLabel(
            upload_frame,
            text="Upload Document",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        )
        upload_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        upload_caption = ctk.CTkLabel(
            upload_frame,
            text=".docx, .odt, .pdf",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        )
        upload_caption.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")
        
        upload_button = ctk.CTkButton(
            upload_frame,
            text="Browse",
            command=self.upload_file,
            fg_color="#4A4A4A",
            hover_color="#3A3A3A",
            text_color="white",
            corner_radius=6
        )
        upload_button.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        self.file_info_label = ctk.CTkLabel(
            upload_frame,
            text="No file selected",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        )
        self.file_info_label.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="w")
        
        # Speed section
        speed_frame = ctk.CTkFrame(left_frame, corner_radius=10, fg_color="#2E2E2E")
        speed_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        speed_label = ctk.CTkLabel(
            speed_frame,
            text="Typing Speed",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        )
        speed_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        speed_options = {
            "Ultra Fast": 0.001,
            "Very Fast": 0.005,
            "Fast": 0.01,
            "Medium": 0.03,
            "Slow": 0.05
        }
        
        speed_option_menu = ctk.CTkOptionMenu(
            speed_frame,
            values=list(speed_options.keys()),
            command=lambda value: self.typing_speed_var.set(speed_options[value]),
            corner_radius=6,
            fg_color="#4A4A4A",
            button_color="#4A4A4A",
            button_hover_color="#3A3A3A",
            text_color="white"
        )
        speed_option_menu.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # Start button
        self.start_button = ctk.CTkButton(
            left_frame,
            text="Start Typing",
            command=self.start_typer,
            state="disabled",
            fg_color="#FFFFFF",
            hover_color="#E0E0E0",
            text_color="#1C2526",
            corner_radius=6,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.start_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Right column: Preview and Analyzer
        right_frame = ctk.CTkFrame(main_frame, corner_radius=10, fg_color="#2E2E2E")
        right_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=5, pady=5)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        self.preview_analyzer_tabview = ctk.CTkTabview(
            right_frame,
            corner_radius=10,
            fg_color="#2E2E2E",
            segmented_button_fg_color="#4A4A4A",
            segmented_button_selected_color="#FFFFFF",
            segmented_button_selected_hover_color="#E0E0E0",
            text_color="white"
        )
        self.preview_analyzer_tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.preview_analyzer_tabview.grid_remove()
        
        preview_tab = self.preview_analyzer_tabview.add("Preview")
        preview_tab.grid_columnconfigure(0, weight=1)
        preview_tab.grid_rowconfigure(1, weight=1)
        
        preview_label = ctk.CTkLabel(
            preview_tab,
            text="Document Content",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        preview_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.preview_text = ctk.CTkTextbox(
            preview_tab,
            height=400,
            wrap="word",
            corner_radius=6,
            fg_color="#1C2526",
            text_color="white"
        )
        self.preview_text.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        analyzer_tab = self.preview_analyzer_tabview.add("Analyzer")
        analyzer_tab.grid_columnconfigure(0, weight=1)
        analyzer_tab.grid_rowconfigure(1, weight=1)
        
        analyzer_label = ctk.CTkLabel(
            analyzer_tab,
            text="Format Analysis",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        analyzer_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.analyzer_text = ctk.CTkTextbox(
            analyzer_tab,
            height=400,
            wrap="word",
            corner_radius=6,
            fg_color="#1C2526",
            text_color="white"
        )
        self.analyzer_text.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # Status section
        status_frame = ctk.CTkFrame(main_frame, corner_radius=10, fg_color="#2E2E2E")
        status_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Upload a document to begin",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.images_check = ctk.CTkCheckBox(
            status_frame,
            text="Contains Images",
            variable=self.contains_images_var,
            font=ctk.CTkFont(size=12),
            fg_color="#4A4A4A",
            text_color="white"
        )
        self.images_check.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        self.images_check.grid_remove()
        
        self.progress_frame = ctk.CTkFrame(status_frame, corner_radius=10, fg_color="#2E2E2E")
        self.progress_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.progress_frame.grid_remove()
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Typing: 0/0 characters (0%)",
            font=ctk.CTkFont(size=12),
            text_color="white"
        )
        self.progress_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            corner_radius=6,
            fg_color="#4A4A4A",
            progress_color="#FFFFFF"
        )
        self.progress_bar.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.progress_bar.set(0)
        
        self.status_message = ctk.CTkLabel(
            self.progress_frame,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.status_message.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="w")
    
    def setup_automation_tab(self, parent):
        """Setup the Automation tab content."""
        main_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#1C2526")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            main_frame,
            text="Automation",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        description = ctk.CTkLabel(
            main_frame,
            text="VClass automation coming soon",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        description.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        coming_soon = ctk.CTkLabel(
            main_frame,
            text="Under Development",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        coming_soon.grid(row=2, column=0, padx=20, pady=20, sticky="w")
    
    def setup_support_tab(self, parent):
        """Setup the Support tab content."""
        main_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#1C2526")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            main_frame,
            text="Support Us",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        caption = ctk.CTkLabel(
            main_frame,
            text="Your support keeps this tool free!",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        caption.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        support_frame = ctk.CTkFrame(main_frame, corner_radius=10, fg_color="#2E2E2E")
        support_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        patreon_button = ctk.CTkButton(
            support_frame,
            text="Patreon",
            command=lambda: self.open_url("https://patreon.com/vclassjailbreaker"),
            fg_color="#4A4A4A",
            hover_color="#3A3A3A",
            text_color="white",
            corner_radius=6
        )
        patreon_button.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        paypal_button = ctk.CTkButton(
            support_frame,
            text="PayPal",
            command=lambda: self.open_url("https://paypal.me/vclassjailbreaker"),
            fg_color="#4A4A4A",
            hover_color="#3A3A3A",
            text_color="white",
            corner_radius=6
        )
        paypal_button.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
    
    def setup_settings_tab(self, parent):
        """Setup the Settings tab content."""
        main_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#1C2526")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            main_frame,
            text="Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        description = ctk.CTkLabel(
            main_frame,
            text="Optimize your experience",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        description.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        settings_frame = ctk.CTkFrame(main_frame, corner_radius=10, fg_color="#2E2E2E")
        settings_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        settings_text = ctk.CTkLabel(
            settings_frame,
            text="""
            • Speed: Lower for accuracy
            • Chunk Size: Smaller for large files
            • Headless: Run in background
            • Screenshots: Verify typing
            """,
            justify="left",
            wraplength=500,
            font=ctk.CTkFont(size=12),
            text_color="white"
        )
        settings_text.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        troubleshoot_header = ctk.CTkLabel(
            main_frame,
            text="Troubleshooting",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        )
        troubleshoot_header.grid(row=3, column=0, padx=20, pady=(20, 10), sticky="w")
        
        troubleshoot_frame = ctk.CTkFrame(main_frame, corner_radius=10, fg_color="#2E2E2E")
        troubleshoot_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        troubleshoot_text = ctk.CTkLabel(
            troubleshoot_frame,
            text="""
            If issues occur:
            • Slow typing speed
            • Reduce chunk size
            • Check credentials
            • Use .docx, .odt, .pdf
            • Simplify formatting
            """,
            justify="left",
            wraplength=500,
            font=ctk.CTkFont(size=12),
            text_color="white"
        )
        troubleshoot_text.grid(row=0, column=0, padx=20, pady=20, sticky="w")
    
    def open_url(self, url):
        """Open URL in default browser."""
        import webbrowser
        webbrowser.open(url)
    
    def change_appearance_mode(self, new_appearance_mode):
        """Change app appearance mode."""
        ctk.set_appearance_mode(new_appearance_mode)
    
    def reset_session(self):
        """Reset all session variables and UI elements."""
        self.api_key_var.set("")
        self.reg_number_var.set("")
        self.password_var.set("")
        self.provider_var.set("Google")
        self.model_var.set("google-gla:gemini-2.0-flash")
        self.typing_speed_var.set(0.03)
        self.chunk_size_var.set(2000)
        self.headless_mode_var.set(True)
        self.doc_type_var.set("Docx / Word Document")
        self.screenshots_var.set(True)
        self.contains_images_var.set(True)
        self.error_correction_var.set(True)
        
        self.file_info_label.configure(text="No file selected")
        self.status_label.configure(text="Upload a document to begin")
        self.start_button.configure(state="disabled")
        
        self.preview_analyzer_tabview.grid_remove()
        self.progress_frame.grid_remove()
        self.images_check.grid_remove()
        
        self.preview_text.delete("0.0", "end")
        self.analyzer_text.delete("0.0", "end")
        
        self.uploaded_file_path = None
        self.file_content = None
        
        self.after(100, lambda: CustomDialog(
            self,
            title="Reset Complete",
            message="Session reset successfully.",
            icon="check",
            option_1="OK"
        ))
    
    def show_info_dialog(self):
        """Show information dialog."""
        CustomDialog(
            self,
            title="VClass AI Typer",
            message="Automates typing into VClass.\nUpload a document and configure settings.",
            icon="info",
            option_1="Got it"
        )
    
    def upload_file(self):
        """Handle file upload."""
        filetypes = [
            ("Word Documents", "*.docx"),
            ("OpenDocument Text", "*.odt"),
            ("PDF Files", "*.pdf"),
            ("All Files", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Select a document",
            filetypes=filetypes
        )
        
        if not file_path:
            return
        
        self.uploaded_file_path = file_path
        file_name = os.path.basename(file_path)
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        class UploadedFile:
            def __init__(self, filename, content):
                self.name = filename
                self._content = content
                self._position = 0
            
            def getvalue(self):
                return self._content
            
            def read(self, size=-1):
                if size < 0:
                    data = self._content[self._position:]
                    self._position = len(self._content)
                else:
                    data = self._content[self._position:self._position + size]
                    self._position += len(data)
                return data
            
            def seek(self, offset, whence=0):
                if whence == 0:
                    self._position = offset
                elif whence == 1:
                    self._position += offset
                elif whence == 2:
                    self._position = len(self._content) + offset
                return self._position
            
            def tell(self):
                return self._position
            
            def close(self):
                pass
                
            def seekable(self):
                return True
                
            def __enter__(self):
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.close()
        
        uploaded_file = UploadedFile(file_name, file_bytes)
        is_valid, validation_result = is_valid_doc(uploaded_file)
        
        if not is_valid:
            CustomDialog(
                self,
                title="Invalid Document",
                message=f"Invalid document: {validation_result}",
                icon="cancel",
                option_1="OK"
            )
            return
        
        self.file_info = validation_result
        
        try:
            self.file_content = extract_file_content(uploaded_file, validation_result)
            
            self.file_info_label.configure(
                text=f"File: {file_name} ({validation_result['size']/1024:.1f} KB)"
            )
            
            self.status_label.configure(
                text=f"✅ {validation_result['type'].upper()} file loaded",
                text_color="#FFFFFF"
            )
            
            self.start_button.configure(state="normal")
            
            self.preview_analyzer_tabview.grid()
            self.preview_text.delete("0.0", "end")
            self.preview_text.insert("0.0", self.file_content)
            
            file_analyzed = analyze_docx(uploaded_file)
            self.analyzer_text.delete("0.0", "end")
            self.analyzer_text.insert("0.0", file_analyzed)
            
            self.images_check.grid()
            
        except Exception as e:
            CustomDialog(
                self,
                title="Error",
                message=f"Error processing document: {str(e)}",
                icon="cancel",
                option_1="OK"
            )
            logger.error(f"Processing error: {str(e)}")
    
    def start_typer(self):
        """Start the document typing process."""
        if not self.uploaded_file_path:
            CustomDialog(
                self,
                title="No Document",
                message="Please upload a document first.",
                icon="cancel",
                option_1="OK"
            )
            return
        
        self.progress_frame.grid()
        self.progress_bar.set(0)
        self.progress_label.configure(text="Typing: 0/0 characters (0%)")
        self.status_message.configure(text="Preparing document...")
        
        threading.Thread(target=self.process_document, daemon=True).start()
    
    def process_document(self):
        """Process the document and type it."""
        try:
            self.start_button.configure(state="disabled")
            
            delay = self.typing_speed_var.get()
            error_correction = self.error_correction_var.get()
            model_name = self.model_var.get()
            
            # Show preparation dialog
            self.after(0, lambda: self.update_status("Preparing to type..."))
            
            def progress_callback(chars_typed, total_chars):
                """Callback to update progress"""
                progress_percent = min(1.0, chars_typed / total_chars)
                self.after(0, lambda: self.update_progress_ui(chars_typed, total_chars, progress_percent))
            
            # Get document text
            try:
                if self.uploaded_file_path.endswith('.docx'):
                    document_text = extract_text_from_docx(self.uploaded_file_path)
                else:
                    with open(self.uploaded_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        document_text = f.read()
            except Exception as e:
                raise Exception(f"Failed to read document: {str(e)}")
            
            if not document_text:
                raise Exception("No text content found in document")
                
            # Initialize typing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            retyper = DocumentRetyper(delay=delay, model_name=model_name)
            
            # Countdown dialog
            self.after(0, lambda: CustomDialog(
                self,
                title="Prepare Cursor",
                message="Position your cursor and click OK.\nTyping starts in 5 seconds...",
                icon="info",
                option_1="OK"
            ))
            
            time.sleep(5)  # Give time to position cursor
            
            mouse = MouseController()
            cursor_position = mouse.position
            
            self.update_status("Typing in progress...")
            
            # Initialize retyper
            loop.run_until_complete(retyper.async_init())
            
            # Get document info
            total_chars = len(document_text)
            
            # Start typing with progress updates
            async def type_with_progress():
                try:
                    return await retyper.retype_document_with_real_typing(
                        document_text,
                        cursor_position,
                        error_correction,
                        progress_callback=progress_callback
                    )
                except Exception as e:
                    raise Exception(f"Typing error: {str(e)}")
            
            retyped_content = loop.run_until_complete(type_with_progress())
            
            if retyped_content:
                self.after(0, self.complete_typing)
            else:
                raise Exception("No content was typed")
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"Typing error: {error_message}")
            self.after(0, lambda: self.handle_typing_error(error_message))
        finally:
            if 'loop' in locals():
                loop.close()
    
    def update_progress_ui(self, chars_typed, total_chars, progress_percent):
        """Update progress UI."""
        self.progress_bar.set(progress_percent)
        self.progress_label.configure(
            text=f"Typing: {chars_typed}/{total_chars} ({int(progress_percent*100)}%)"
        )
    
    def update_status(self, message):
        """Update status message."""
        self.status_message.configure(text=message)
    
    def complete_typing(self):
        """Complete typing process."""
        self.progress_bar.set(1.0)
        self.status_message.configure(
            text="✅ Typing complete!",
            text_color="#FFFFFF"
        )
        self.start_button.configure(state="normal")
        
        self.after(100, lambda: CustomDialog(
            self,
            title="Typing Complete",
            message="Document typed successfully!",
            icon="check",
            option_1="OK"
        ))
    
    def handle_typing_error(self, error_message):
        """Handle typing error."""
        self.status_message.configure(
            text=f"Error: {error_message}",
            text_color="#FFFFFF"
        )
        self.start_button.configure(state="normal")
        
        self.after(100, lambda: CustomDialog(
            self,
            title="Typing Error",
            message=f"Error: {error_message}",
            icon="cancel",
            option_1="OK"
        ))

if __name__ == "__main__":
    app = AITyper()
    app.mainloop()