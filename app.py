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
from CTkMessagebox import CTkMessagebox
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
ctk.set_appearance_mode("System")  # "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

class ScrollableFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

class ScrollableContentFrame(ctk.CTkScrollableFrame):
    """Custom scrollable frame for main content."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

class VClassAITyper(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("VClass AI Typer Agent")
        self.geometry("1100x700")
        self.minsize(500, 600)
        # self.iconbitmap(default="assets/icon.ico")  # Replace with your icon path
        
        # App state
        self.sidebar_visible = True  # Track sidebar visibility
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
        
        # Bind window resize event for responsiveness
        self.bind("<Configure>", self.on_resize)

        # Create layout
        self.create_layout()
        
    def create_layout(self):
        # Main layout with two columns: sidebar and content
        self.grid_columnconfigure(0, weight=0)  # Sidebar column
        self.grid_columnconfigure(1, weight=1)  # Main content column
        self.grid_rowconfigure(0, weight=1)

        # Create sidebar
        self.sidebar_frame = self.create_sidebar()

        # Create main content area
        self.create_main_content()

        # Add a floating toggle button for small screens
        self.toggle_button = ctk.CTkButton(
            self,
            text="☰",
            width=40,
            height=40,
            corner_radius=20,
            command=self.toggle_sidebar,
            fg_color="#0078D7",
            hover_color="#005A9E",
            text_color="white"
        )
        self.toggle_button.place(x=10, y=10)  # Initially visible
    
    def create_sidebar(self):
        """Create the application sidebar with settings"""
        sidebar_frame = ctk.CTkFrame(self, width=150, corner_radius=0)
        sidebar_frame.grid(row=0, column=0, sticky="nsew")
        sidebar_frame.grid_rowconfigure(20, weight=1)  # Push footer to bottom
        
        # Add toggle button to hide/show sidebar
        toggle_button = ctk.CTkButton(
            sidebar_frame,
            text="☰",
            width=30,
            command=self.toggle_sidebar
        )
        toggle_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Logo and title
        logo_label = ctk.CTkLabel(
            sidebar_frame, 
            text="VClass AI Typer",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(5, 10))
        
        caption = ctk.CTkLabel(
            sidebar_frame, 
            text="Automation Tool for VClass",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        caption.grid(row=1, column=0, padx=20, pady=(0, 5))
        
        # Settings header
        settings_label = ctk.CTkLabel(
            sidebar_frame, 
            text="Settings",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        settings_label.grid(row=2, column=0, padx=20, pady=(5, 5), sticky="w")
        
        # API Preferences
        api_label = ctk.CTkLabel(
            sidebar_frame, 
            text="API Preferences",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        api_label.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="w")
        
        # Provider selection
        # provider_frame = ctk.CTkFrame(sidebar_frame)
        # provider_frame.grid(row=4, column=0, padx=20, pady=(5, 5), sticky="ew")
        
        # provider_label = ctk.CTkLabel(provider_frame, text="Provider:")
        # provider_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # provider_menu = ctk.CTkOptionMenu(
        #     provider_frame,
        #     values=["Google", "OpenRouter", "Groq", "Claude"],
        #     variable=self.provider_var,
        #     width=120,
        #     command=self.update_api_label
        # )
        # provider_menu.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        # API Key input
        api_key_frame = ctk.CTkFrame(sidebar_frame)
        api_key_frame.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        self.api_key_label = ctk.CTkLabel(api_key_frame, text="Google API Key:")
        self.api_key_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        api_key_entry = ctk.CTkEntry(
            api_key_frame,
            width=150,
            placeholder_text="Enter API Key",
            show="•",
            textvariable=self.api_key_var
        )
        api_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        # Model selection
        model_label = ctk.CTkLabel(sidebar_frame, text="AI Model:")
        model_label.grid(row=6, column=0, padx=20, pady=(5, 5), sticky="w")
        
        model_options = [
            "google-gla:gemini-2.0-flash",
            "google-gla:gemini-1.5-flash",
            # "google-gla:gemini-2.0-pro",
            # "mistral:mistral-large-latest",
            "mistral-small-latest",
            # "groq:llama3-70b-8192",
            "groq:deepseek-r1-distill-llama-70b",
            "groq:gemma2-9b-it",
            "groq:llama3-8b-8192",
            # "groq:llama-3.3-70b-versatile",
            # "groq:qwen-2.5-32b",
            "groq:mistral-saba-24b"
        ]
        
        model_menu = ctk.CTkOptionMenu(
            sidebar_frame,
            values=model_options,
            variable=self.model_var,
            width=200
        )
        model_menu.grid(row=7, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Anonymous Credentials
        # creds_label = ctk.CTkLabel(
        #     sidebar_frame, 
        #     text="Anonymous Credentials",
        #     font=ctk.CTkFont(size=14, weight="bold")
        # )
        # creds_label.grid(row=8, column=0, padx=20, pady=(10, 5), sticky="w")
        
        # # Registration Number
        # reg_frame = ctk.CTkFrame(sidebar_frame)
        # reg_frame.grid(row=9, column=0, padx=20, pady=(5, 5), sticky="ew")
        
        # reg_label = ctk.CTkLabel(reg_frame, text="Rank Number:")
        # reg_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # reg_entry = ctk.CTkEntry(
        #     reg_frame,
        #     width=120,
        #     placeholder_text="Enter Rank #",
        #     textvariable=self.reg_number_var
        # )
        # reg_entry.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        # Password
        # pass_frame = ctk.CTkFrame(sidebar_frame)
        # pass_frame.grid(row=10, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # pass_label = ctk.CTkLabel(pass_frame, text="Hash Passcode:")
        # pass_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # pass_entry = ctk.CTkEntry(
        #     pass_frame,
        #     width=120,
        #     placeholder_text="Enter Hash",
        #     show="•",
        #     textvariable=self.password_var
        # )
        # pass_entry.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        # Browser Settings
        browser_label = ctk.CTkLabel(
            sidebar_frame, 
            text="Advanced Settings",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        browser_label.grid(row=11, column=0, padx=20, pady=(5, 5), sticky="w")
        
        # Typing Speed
        speed_label = ctk.CTkLabel(sidebar_frame, text=f"Typing Speed: {self.typing_speed_var.get():.3f}s")
        speed_label.grid(row=12, column=0, padx=20, pady=(5, 0), sticky="w")
        
        speed_slider = ctk.CTkSlider(
            sidebar_frame,
            from_=0.001,
            to=0.1,
            variable=self.typing_speed_var,
            command=lambda v: speed_label.configure(text=f"Typing Speed: {float(v):.3f}s")
        )
        speed_slider.grid(row=13, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Chunk Size
        chunk_label = ctk.CTkLabel(sidebar_frame, text=f"Chunk Size: {self.chunk_size_var.get()}")
        chunk_label.grid(row=14, column=0, padx=20, pady=(5, 0), sticky="w")
        
        chunk_slider = ctk.CTkSlider(
            sidebar_frame,
            from_=500,
            to=10000,
            variable=self.chunk_size_var,
            command=lambda v: chunk_label.configure(text=f"Chunk Size: {int(v)}")
        )
        chunk_slider.grid(row=15, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Additional options
        options_frame = ctk.CTkFrame(sidebar_frame)
        options_frame.grid(row=16, column=0, padx=20, pady=(5, 10), sticky="ew")
        options_frame.grid_columnconfigure(0, weight=1)
        options_frame.grid_columnconfigure(1, weight=1)
        
        headless_switch = ctk.CTkSwitch(
            options_frame,
            text="Headless Mode",
            variable=self.headless_mode_var
        )
        headless_switch.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        screenshots_switch = ctk.CTkSwitch(
            options_frame,
            text="Take Screenshots",
            variable=self.screenshots_var
        )
        screenshots_switch.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        error_correction_switch = ctk.CTkSwitch(
            options_frame,
            text="Error Correction",
            variable=self.error_correction_var
        )
        error_correction_switch.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # Reset button
        reset_button = ctk.CTkButton(
            sidebar_frame,
            text="Reset Session",
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
            command=self.reset_session
        )
        reset_button.grid(row=17, column=0, padx=20, pady=(10, 10), sticky="ew")
        
        # Theme switcher
        appearance_mode_menu = ctk.CTkOptionMenu(
            sidebar_frame,
            values=["System", "Light", "Dark"],
            command=self.change_appearance_mode
        )
        appearance_mode_menu.grid(row=18, column=0, padx=20, pady=(10, 0), sticky="ew")
        
        # Footer
        footer = ctk.CTkLabel(
            sidebar_frame,
            text="© 2025 | Made with ❤️ in Uganda",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        footer.grid(row=21, column=0, padx=20, pady=(0, 10))
        
        return sidebar_frame
    
    def toggle_sidebar(self):
        """Toggle the visibility of the sidebar"""
        if self.sidebar_visible:
            self.sidebar_frame.grid_remove()
            self.toggle_button.place(x=10, y=10)  # Keep toggle button visible
        else:
            self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
            self.toggle_button.place_forget()  # Hide toggle button when sidebar is visible
        self.sidebar_visible = not self.sidebar_visible

    def on_resize(self, event):
        """Handle window resize events for responsiveness"""
        width = self.winfo_width()
        if width < 800 and self.sidebar_visible:
            self.toggle_sidebar()  # Automatically hide sidebar for small screens
        elif width >= 800 and not self.sidebar_visible:
            self.toggle_sidebar()  # Automatically show sidebar for larger screens

    def create_main_content(self):
        """Create the main content area with tabs and scrolling."""
        content_frame = ctk.CTkFrame(self, corner_radius=10)
        content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Add a scrollable frame for the main content
        scrollable_content = ScrollableContentFrame(content_frame)
        scrollable_content.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        scrollable_content.grid_columnconfigure(0, weight=1)

        # Add a header with improved spacing
        header_frame = ctk.CTkFrame(scrollable_content, corner_radius=10)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 20))
        header_frame.grid_columnconfigure(0, weight=1)

        header_label = ctk.CTkLabel(
            header_frame,
            text="VClass AI JailBreaker",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#0078D7"
        )
        header_label.grid(row=0, column=0, sticky="w", padx=20, pady=10)

        # Add a modern info button
        info_button = ctk.CTkButton(
            header_frame,
            text="ℹ️",
            width=40,
            height=40,
            corner_radius=20,
            command=self.show_info_dialog,
            fg_color="#0078D7",
            hover_color="#005A9E",
            text_color="white"
        )
        info_button.grid(row=0, column=1, sticky="e", padx=20, pady=10)

        instructions_button = ctk.CTkButton(
            header_frame,
            text="Learn To Use The Agent",
            command=lambda: self.toggle_widget_visibility(instructions_content)
        )
        instructions_button.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        instructions_content = ctk.CTkFrame(header_frame)
        instructions_content.grid(row=1, column=2, padx=10, pady=(0, 10), sticky="ew")
        instructions_content.grid_remove()  # Initially hidden

        instructions_text = ctk.CTkLabel(
            instructions_content,
            text="""
            1. Upload a .docx file using the file uploader
            2. Adjust typing speed if needed
            3. Open the target application where you want the text to be typed
            4. Click "Start AI Retyper"
            5. You'll have 5 seconds to position your cursor where typing should begin
            6. Stay still and let the typing complete
            """,
            justify="left",
            wraplength=500
        )
        instructions_text.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Tab view
        self.tabview = ctk.CTkTabview(scrollable_content)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=0, pady=(15, 2))

        # Create tabs
        tab1 = self.tabview.add("🔧 Typer Agent Document")
        tab2 = self.tabview.add("⚙️ Automation")
        tab3 = self.tabview.add("⭐ Support Us")
        tab4 = self.tabview.add("⚙️ Settings")

        # Configure tab grids
        for tab in [tab1, tab2, tab3, tab4]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(20, weight=1)  # For scrollable content

        # Set up each tab content
        self.setup_typer_tab(tab1)
        self.setup_automation_tab(tab2)
        self.setup_support_tab(tab3)
        self.setup_settings_tab(tab4)
        
    def setup_typer_tab(self, parent):
        """Setup the Document Typer tab content"""
        # Upload section
        upload_frame = ctk.CTkFrame(parent)
        upload_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        upload_label = ctk.CTkLabel(
            upload_frame,
            text="📤 Upload Your Document",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        upload_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        upload_caption = ctk.CTkLabel(
            upload_frame,
            text="Upload your document below or click Browse Files.\nSupported formats: .docx, .odt, .pdf",
            justify="left",
            text_color="gray"
        )
        upload_caption.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        
        upload_button = ctk.CTkButton(
            upload_frame,
            text="Browse Files",
            command=self.upload_file
        )
        upload_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        self.file_info_label = ctk.CTkLabel(
            upload_frame,
            text="No file selected",
            text_color="gray"
        )
        self.file_info_label.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="w")
        
        # Processing section (initially hidden)
        self.processing_frame = ctk.CTkFrame(parent)
        self.processing_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.processing_frame.grid_remove()  # Initially hidden
        
        # Preferences section (initially hidden)
        self.preferences_frame = ctk.CTkFrame(parent)
        self.preferences_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.preferences_frame.grid_remove()  # Initially hidden
        
        preferences_button = ctk.CTkButton(
            self.preferences_frame,
            text="Preferences (Don't Change Anything)",
            command=lambda: self.toggle_widget_visibility(preferences_content)
        )
        preferences_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        preferences_content = ctk.CTkFrame(self.preferences_frame)
        preferences_content.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        preferences_content.grid_remove()  # Initially hidden
        
        caption = ctk.CTkLabel(
            preferences_content,
            text="The lower (0.001) the slider the faster the agent and the higher the slower.\nDefault: 0.03 (Human Typing With Accuracy 85%)",
            justify="left",
            text_color="gray"
        )
        caption.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        speed_options = {
            "Ultra Fast (AI Speed)": 0.001,
            "Very Fast": 0.005,
            "Fast": 0.01,
            "Medium (Human-like)": 0.03,
            "Slow": 0.05
        }
        
        speed_option_frame = ctk.CTkFrame(preferences_content)
        speed_option_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        speed_option_label = ctk.CTkLabel(speed_option_frame, text="Speed Preset:")
        speed_option_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        speed_option_menu = ctk.CTkOptionMenu(
            speed_option_frame,
            values=list(speed_options.keys()),
            command=lambda value: self.typing_speed_var.set(speed_options[value])
        )
        speed_option_menu.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        # Action buttons
        action_frame = ctk.CTkFrame(parent)
        action_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        
        self.start_button = ctk.CTkButton(
            action_frame,
            text="Start AI Typer",
            command=self.start_typer,
            state="disabled",
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.start_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Preview section (initially hidden)
        self.preview_frame = ctk.CTkFrame(parent)
        self.preview_frame.grid(row=2, column=6, padx=10, pady=10, sticky="ew")
        self.preview_frame.grid_remove()  # Initially hidden
        
        preview_button = ctk.CTkButton(
            self.preview_frame,
            text="📄 Document Preview",
            command=lambda: self.toggle_widget_visibility(preview_content)
        )
        preview_button.grid(row=0, column=6, padx=10, pady=10, sticky="ew")
        
        preview_content = ctk.CTkFrame(self.preview_frame)
        preview_content.grid(row=2, column=6, padx=10, pady=(0, 10), sticky="ew")
        preview_content.grid_remove()  # Initially hidden
        
        preview_label = ctk.CTkLabel(
            preview_content,
            text="🧾 File Content:",
            font=ctk.CTkFont(weight="bold")
        )
        preview_label.grid(row=2, column=6, padx=10, pady=(10, 0), sticky="w")
        
        self.preview_text = ctk.CTkTextbox(
            preview_content,
            width=500,
            height=300,
            wrap="word"
        )
        self.preview_text.grid(row=2, column=6, padx=10, pady=10, sticky="nsew")
        
        # Analyzer section (initially hidden)
        self.analyzer_frame = ctk.CTkFrame(parent)
        self.analyzer_frame.grid(row=1, column=6, padx=10, pady=10, sticky="ew")
        self.analyzer_frame.grid_remove()  # Initially hidden
        
        analyzer_button = ctk.CTkButton(
            self.analyzer_frame,
            text="🔑 Analyzer Formatter",
            command=lambda: self.toggle_widget_visibility(analyzer_content)
        )
        analyzer_button.grid(row=0, column=6, padx=10, pady=10, sticky="ew")
        
        analyzer_content = ctk.CTkFrame(self.analyzer_frame)
        analyzer_content.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        analyzer_content.grid_remove()  # Initially hidden
        
        analyzer_label = ctk.CTkLabel(
            analyzer_content,
            text="Document Contains the following Formats as Word Document Provided:",
            font=ctk.CTkFont(weight="bold")
        )
        analyzer_label.grid(row=0, column=6, padx=10, pady=(10, 0), sticky="w")
        
        self.analyzer_text = ctk.CTkTextbox(
            analyzer_content,
            width=500,
            height=300,
            wrap="word"
        )
        self.analyzer_text.grid(row=1, column=6, padx=10, pady=10, sticky="nsew")
        
        # Status section
        self.status_frame = ctk.CTkFrame(parent)
        self.status_frame.grid(row=7, column=0, padx=10, pady=10, sticky="ew")
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Upload a document to begin",
            text_color="gray"
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Images checkbox
        self.images_check = ctk.CTkCheckBox(
            self.status_frame,
            text="Images Inside (To avoid image download)",
            variable=self.contains_images_var
        )
        self.images_check.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        self.images_check.grid_remove()  # Initially hidden
        
        # Progress section (initially hidden)
        self.progress_frame = ctk.CTkFrame(parent)
        self.progress_frame.grid(row=8, column=0, padx=10, pady=10, sticky="ew")
        self.progress_frame.grid_remove()  # Initially hidden
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Typing: 0/0 characters (0%)"
        )
        self.progress_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.progress_bar.set(0)
        
        self.status_message = ctk.CTkLabel(
            self.progress_frame,
            text="",
            text_color="gray"
        )
        self.status_message.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
    
    def setup_automation_tab(self, parent):
        """Setup the Automation tab content"""
        header = ctk.CTkLabel(
            parent,
            text="Automatic Typer",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        description = ctk.CTkLabel(
            parent,
            text="Here the agent will login to your vclass and submit your document",
            text_color="gray"
        )
        description.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        
        caption = ctk.CTkLabel(
            parent,
            text="For Faster Agent it's for payment",
            text_color="gray70"
        )
        caption.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")
        
        coming_soon = ctk.CTkLabel(
            parent,
            text="🚧 Coming Soon 🚀",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        coming_soon.grid(row=3, column=0, padx=20, pady=(20, 10), sticky="w")
        
        stay_tuned = ctk.CTkLabel(
            parent,
            text="🔜 Stay Tuned! 🌟",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        stay_tuned.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="w")
        
        coming_details = ctk.CTkLabel(
            parent,
            text="• 🛠️ We're working hard to bring this feature to life!\n• 📅 Expected release: TBD\n• 💡 Have suggestions? Let us know!",
            justify="left"
        )
        coming_details.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="w")
        
        info_box = ctk.CTkFrame(parent)
        info_box.grid(row=6, column=0, padx=20, pady=20, sticky="ew")
        
        info_label = ctk.CTkLabel(
            info_box,
            text="✨ Exciting updates are on the way. Keep an eye out! 👀",
            text_color="#0096FF"
        )
        info_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Advanced Options expander
        options_button = ctk.CTkButton(
            parent,
            text="Advanced Options",
            command=lambda: self.toggle_widget_visibility(advanced_frame)
        )
        options_button.grid(row=7, column=0, padx=20, pady=(20, 0), sticky="ew")
        
        advanced_frame = ctk.CTkFrame(parent)
        # advanced_frame.grid(row=8, column=0, padx=20, pady=(5,
        advanced_frame = ctk.CTkFrame(parent)
        advanced_frame.grid(row=8, column=0, padx=20, pady=(5, 20), sticky="ew")
        advanced_frame.grid_remove()  # Initially hidden
        
        advanced_caption = ctk.CTkLabel(
            advanced_frame,
            text="Keep in mind to reset just refresh the page and don't set anything unnecessarily.",
            text_color="gray",
            wraplength=500
        )
        advanced_caption.grid(row=0, column=0, padx=10, pady=(10, 10), sticky="w", columnspan=2)
        
        col1 = ctk.CTkFrame(advanced_frame)
        col1.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        col2 = ctk.CTkFrame(advanced_frame)
        col2.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        
        timer_label = ctk.CTkLabel(col1, text="Override Timer")
        timer_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        timer_entry = ctk.CTkEntry(col1, placeholder_text="Leave empty to use sidebar value")
        timer_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        ghost_label = ctk.CTkLabel(col1, text="Ghost Typer")
        ghost_label.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="w")
        
        ghost_entry = ctk.CTkEntry(col1, placeholder_text="Leave empty to use sidebar value")
        ghost_entry.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        speed_label = ctk.CTkLabel(col2, text="Override Typing Speed")
        speed_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        speed_entry = ctk.CTkSlider(col2, from_=0, to=100)
        speed_entry.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        speed_help = ctk.CTkLabel(col2, text="Set to 0 to use sidebar value", text_color="gray")
        speed_help.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
    
    def setup_support_tab(self, parent):
        """Setup the Support Us tab content"""
        header = ctk.CTkLabel(
            parent,
            text="Contribution To Repo",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        caption = ctk.CTkLabel(
            parent,
            text="Leave a star ⭐",
            text_color="gray"
        )
        caption.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        
        description = ctk.CTkLabel(
            parent,
            text="Please Submit a PR in case of a Push and it shall be reviewed.",
            text_color="gray70"
        )
        description.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")
        
        support_header = ctk.CTkLabel(
            parent,
            text="Support Us",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        support_header.grid(row=3, column=0, padx=20, pady=(20, 10), sticky="w")
        
        description = ctk.CTkLabel(
            parent,
            text="If you find this tool helpful, consider supporting us!",
        )
        description.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Support buttons
        support_frame = ctk.CTkFrame(parent)
        support_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        support_frame.grid_columnconfigure(0, weight=1)
        
        patreon_button = ctk.CTkButton(
            support_frame,
            text="Support us on Patreon",
            command=lambda: self.open_url("https://patreon.com/vclassjailbreaker"),
            fg_color="#FF424D",
            hover_color="#E23B41"
        )
        patreon_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        binance_button = ctk.CTkButton(
            support_frame,
            text="Support us on Binance",
            command=lambda: self.open_url("https://paypal.me/vclassjailbreaker"),
            fg_color="#F0B90B",
            hover_color="#D6A60A",
            text_color="#000000"
        )
        binance_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        paypal_button = ctk.CTkButton(
            support_frame,
            text="Support us on PayPal",
            command=lambda: self.open_url("https://paypal.me/vclassjailbreaker"),
            fg_color="#003087",
            hover_color="#00287A"
        )
        paypal_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
    
    def setup_settings_tab(self, parent):
        """Setup the Settings tab content"""
        header = ctk.CTkLabel(
            parent,
            text="Settings Guide",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        description = ctk.CTkLabel(
            parent,
            text="The Automation process for the Agent to Login to your vclass and also to submit your document",
        )
        description.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        
        caption = ctk.CTkLabel(
            parent,
            text="Coming Soon: But first support to try for Free and Remember we are not responsible for anything.",
            text_color="gray"
        )
        caption.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Settings tips
        settings_frame = ctk.CTkFrame(parent)
        settings_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        settings_text = ctk.CTkLabel(
            settings_frame,
            text="""
            • Typing Speed: Reduce this for more accurate typing (recommended: 20-25 chars/sec)
            • Chunk Size: For larger documents, smaller chunks are processed more reliably
            • Headless Mode: Run the browser invisibly in the background
            • Screenshots: Capture images to verify the document was typed correctly
            """,
            justify="left",
            wraplength=500
        )
        settings_text.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Troubleshooting tips
        troubleshoot_header = ctk.CTkLabel(
            parent,
            text="Troubleshooting",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        troubleshoot_header.grid(row=4, column=0, padx=20, pady=(20, 10), sticky="w")
        
        troubleshoot_frame = ctk.CTkFrame(parent)
        troubleshoot_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        
        troubleshoot_text = ctk.CTkLabel(
            troubleshoot_frame,
            text="""
            If the automation is not working correctly:
            1. Try a slower typing speed (15-20 chars/sec)
            2. Use smaller chunk sizes (2000-3000 chars)
            3. Make sure your login credentials are correct
            4. Check that the document format is supported (.odt, .docx, .py, .md)
            5. For complex documents, consider simplifying the formatting
            """,
            justify="left",
            wraplength=500
        )
        troubleshoot_text.grid(row=0, column=0, padx=20, pady=20, sticky="w")
    
    # Helper methods
    def toggle_widget_visibility(self, widget):
        """Toggle visibility of a widget"""
        if widget.winfo_viewable():
            widget.grid_remove()
        else:
            widget.grid()
    
    def update_api_label(self, provider_name):
        """Update API key label based on provider selection"""
        self.api_key_label.configure(text=f"{provider_name} API Key:")
    
    def open_url(self, url):
        """Open URL in default browser"""
        import webbrowser
        webbrowser.open(url)
    
    def change_appearance_mode(self, new_appearance_mode):
        """Change app appearance mode (light/dark)"""
        ctk.set_appearance_mode(new_appearance_mode)
    
    def reset_session(self):
        """Reset all session variables and UI elements"""
        # Reset variables
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
        
        # Reset UI state
        self.file_info_label.configure(text="No file selected")
        self.status_label.configure(text="Upload a document to begin")
        self.start_button.configure(state="disabled")
        
        # Hide dynamic components
        self.processing_frame.grid_remove()
        self.preferences_frame.grid_remove()
        self.preview_frame.grid_remove()
        self.analyzer_frame.grid_remove()
        self.progress_frame.grid_remove()
        self.images_check.grid_remove()
        
        # Clear text areas
        self.preview_text.delete("0.0", "end")
        self.analyzer_text.delete("0.0", "end")
        
        # Reset file info
        self.uploaded_file_path = None
        self.file_content = None
        
        # Show confirmation
        CTkMessagebox(
            title="Reset Complete",
            message="Session has been reset successfully.",
            icon="check",
            option_1="OK"
        )
    
    def show_info_dialog(self):
        """Show information dialog"""
        info_dialog = CTkMessagebox(
            title="VClass AI Typer",
            message="This application automates the process of typing documents into the VClass online editor.\n\nUpload your document, provide your credentials, and let the automation handle the rest.",
            icon="info",
            option_1="Got it"
        )
    
    def upload_file(self):
        """Handle file upload"""
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
        
        # Read file content
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        # Create a temporary file-like object
        # class UploadedFile:
        #     def __init__(self, filename, content):
        #         self.name = filename
        #         self._content = content
            
        #     def getvalue(self):
        #         return self._content
        
        # uploaded_file = UploadedFile(file_name, file_bytes)
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
                if whence == 0:  # SEEK_SET
                    self._position = offset
                elif whence == 1:  # SEEK_CUR
                    self._position += offset
                elif whence == 2:  # SEEK_END
                    self._position = len(self._content) + offset
                return self._position
            
            def tell(self):
                return self._position
            
            def close(self):
                pass  # Nothing to close as we're using an in-memory buffer
                
            # Make this object work with context managers (with statements)
            def __enter__(self):
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.close()
        uploaded_file = UploadedFile(file_name, file_bytes)
        # Validate document
        is_valid, validation_result = is_valid_doc(uploaded_file)
        
        if not is_valid:
            CTkMessagebox(
                title="Invalid Document",
                message=f"Invalid document: {validation_result}",
                icon="cancel",
                option_1="OK"
            )
            return
        
        self.file_info = validation_result
        
        try:
            self.file_content = extract_file_content(uploaded_file, validation_result)
            
            # Update UI
            self.file_info_label.configure(
                text=f"File: {file_name} ({validation_result['size']/1024:.1f} KB)"
            )
            
            # Show success message
            self.status_label.configure(
                text=f"🚨 Valid {validation_result['type'].upper()} file: {file_name} detected ({validation_result['size']/1024:.1f} KB)",
                text_color="#28a745"
            )
            
            # Enable start button
            self.start_button.configure(state="normal")
            
            # Show preferences frame
            self.preferences_frame.grid()
            
            # Show preview frame
            self.preview_frame.grid()
            self.preview_text.delete("0.0", "end")
            self.preview_text.insert("0.0", self.file_content)
            
            # Show analyzer frame
            self.analyzer_frame.grid()
            file_analyzed = analyze_docx(uploaded_file)
            self.analyzer_text.delete("0.0", "end")
            self.analyzer_text.insert("0.0", file_analyzed)
            
            # Show images checkbox
            self.images_check.grid()
            
        except Exception as e:
            CTkMessagebox(
                title="Error",
                message=f"Error processing document: {str(e)}",
                icon="cancel",
                option_1="OK"
            )
            logger.error(f"Processing error: {str(e)}")
    
    def start_typer(self):
        """Start the document typing process"""
        if not self.uploaded_file_path:
            CTkMessagebox(
                title="No Document",
                message="Please upload a document first.",
                icon="warning",
                option_1="OK"
            )
            return
        
        # Show progress frame
        self.progress_frame.grid()
        self.progress_bar.set(0)
        self.progress_label.configure(text="Typing: 0/0 characters (0%)")
        self.status_message.configure(text="Preparing document...")
        
        # Start background thread for processing
        threading.Thread(target=self.process_document, daemon=True).start()
    
    def process_document(self):
        """Process the document and type it (run in a separate thread)"""
        try:
            # Disable start button during processing
            self.start_button.configure(state="disabled")
            
            # Setup parameters
            delay = self.typing_speed_var.get()
            error_correction = self.error_correction_var.get()
            model_name = self.model_var.get()
            
            # Create alert for countdown
            # countdown_dialog = CTkMessagebox(
            #     title="Prepare Your Cursor",
            #     message="Typing will begin in 5 seconds...\nPosition your cursor where typing should start!",
            #     icon="info",
            #     option_1="Cancel"
            # )
            
            # Start countdown
            for i in range(5, 0, -1):
                print(f"Typing will begin in {i} seconds...\nPosition your cursor where typing should start!")
                # countdown_dialog.configure(message=f"Typing will begin in {i} seconds...\nPosition your cursor where typing should start!")
                time.sleep(1)
            
            # countdown_dialog.destroy()
            
            # Get cursor position
            mouse = MouseController()
            cursor_position = mouse.position
            
            # Update status
            self.update_status("Don't move the cursor! >>>> Typing in progress...")
            
            # Extract document text
            if self.uploaded_file_path.endswith('.docx'):
                document_text = extract_text_from_docx(self.uploaded_file_path)
            else:
                with open(self.uploaded_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    document_text = f.read()
            
            # Setup async event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Initialize retyper
            retyper = DocumentRetyper(delay=delay, model_name=model_name)
            loop.run_until_complete(retyper.async_init())
            
            # Get document info
            doc_info = loop.run_until_complete(retyper.display_document_info(self.uploaded_file_path))
            
            # Extract total character count for progress tracking
            char_count_match = re.search(r'(\d+) characters', doc_info)
            total_chars = int(char_count_match.group(1)) if char_count_match else len(document_text)
            
            # Create progress callback
            async def update_progress(chars_typed):
                progress_percent = min(1.0, chars_typed / total_chars)
                # Use after method to update UI from background thread
                self.after(0, lambda: self.update_progress(chars_typed, total_chars, progress_percent))
            
            # Start typing
            retyped_content = loop.run_until_complete(
                retyper.retype_document_with_real_typing(
                    document_text,
                    cursor_position,
                    error_correction,
                    progress_callback=update_progress
                )
            )
            
            # Update status on completion
            self.after(0, lambda: self.complete_typing())
            
        except Exception as e:
            # Handle errors
            error_message = str(e)
            self.after(0, lambda: self.handle_typing_error(error_message))
    
    def update_progress(self, chars_typed, total_chars, progress_percent):
        """Update progress UI (called from main thread)"""
        self.progress_bar.set(progress_percent)
        self.progress_label.configure(
            text=f"Typing: {chars_typed}/{total_chars} characters ({int(progress_percent*100)}%)"
        )
    
    def update_status(self, message):
        """Update status message (called from main thread)"""
        self.status_message.configure(text=message)
    
    def complete_typing(self):
        """Complete typing process (called from main thread)"""
        self.progress_bar.set(1.0)
        self.status_message.configure(
            text="✅ Document has been successfully Retyped!",
            text_color="#28a745"
        )
        self.start_button.configure(state="normal")
        
        # Show completion dialog
        CTkMessagebox(
            title="Typing Complete",
            message="Your document has been successfully typed!",
            icon="check",
            option_1="OK"
        )
    
    def handle_typing_error(self, error_message):
        """Handle typing error (called from main thread)"""
        self.status_message.configure(
            text=f"Error occurred: {error_message}",
            text_color="#dc3545"
        )
        self.start_button.configure(state="normal")
        
        # Show error dialog
        CTkMessagebox(
            title="Typing Error",
            message=f"An error occurred during typing:\n{error_message}",
            icon="cancel",
            option_1="OK"
        )

if __name__ == "__main__":
    
    app = VClassAITyper()
    app.mainloop()