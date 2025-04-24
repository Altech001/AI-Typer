import os
import re
import tempfile
import customtkinter as ctk
from PIL import Image
import asyncio
import logging
from pathlib import Path
from pynput.mouse import Controller as MouseController
from utils import extract_file_content, is_valid_doc, display_screenshots
from typer import DocumentRetyper, extract_text_from_docx
from validation import display_error_details
from analzyer import analyze_docx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Customtkinter appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Custom UploadedFile class to mimic Streamlit's UploadedFile
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
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class CustomDialog(ctk.CTkToplevel):
    def __init__(self, master, title, message, icon="info", buttons=["OK"], 
                 default_button="OK", cancel_button=None, width=400, height=200):
        super().__init__(master)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        
        # Center the dialog on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)
        self.geometry(f"+{x}+{y}")
        
        self.result = None
        self.default_button = default_button
        self.cancel_button = cancel_button
        
        # Make the dialog modal
        self.transient(master)
        self.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(self, corner_radius=15)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Create icon label if specified
        icon_text = "ℹ️"
        if icon == "warning":
            icon_text = "⚠️"
        elif icon == "check":
            icon_text = "✅"
        elif icon == "cancel":
            icon_text = "❌"
        elif icon == "question":
            icon_text = "❓"
            
        icon_label = ctk.CTkLabel(main_frame, text=icon_text, font=ctk.CTkFont(size=34))
        icon_label.pack(pady=(15, 5))
        
        # Create message label
        message_label = ctk.CTkLabel(main_frame, text=message, wraplength=width-60, 
                                    font=ctk.CTkFont(size=14))
        message_label.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Create buttons frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 10), padx=10, fill="x")
        
        # Create buttons
        self.button_objects = {}
        
        for i, button_text in enumerate(buttons):
            is_default = button_text == default_button
            is_cancel = button_text == cancel_button
            
            btn = ctk.CTkButton(
                button_frame, 
                text=button_text,
                width=100,
                font=ctk.CTkFont(size=13, weight="bold" if is_default else "normal"),
                fg_color="#3B8ED0" if is_default else ("#FF5555" if is_cancel else "#2B2B2B"),
                hover_color="#36719F" if is_default else ("#CC4444" if is_cancel else "#1F1F1F"),
                command=lambda btn=button_text: self.button_click(btn)
            )
            self.button_objects[button_text] = btn
            btn.pack(side="right" if i == 0 else "left", padx=5)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Bind keyboard shortcuts
        self.bind("<Return>", lambda event: self.button_click(default_button))
        self.bind("<Escape>", lambda event: self.button_click(cancel_button) if cancel_button else None)
        
        # Wait for window to be destroyed
        self.wait_window()
    
    def button_click(self, button_text):
        self.result = button_text
        self.destroy()
    
    def on_close(self):
        if self.cancel_button:
            self.result = self.cancel_button
        else:
            self.result = self.default_button
        self.destroy()
    
    def get(self):
        return self.result

class CountdownDialog(ctk.CTkToplevel):
    def __init__(self, master, seconds=5, callback=None):
        super().__init__(master)
        self.title("Prepare for Typing")
        self.geometry("400x200")
        self.resizable(False, False)
        
        # Center the dialog
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width - 400) / 2)
        y = int((screen_height - 200) / 2)
        self.geometry(f"+{x}+{y}")
        
        self.seconds = seconds
        self.callback = callback
        self.cancelled = False
        self.result = None
        
        # Make the dialog modal
        self.transient(master)
        self.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(self, corner_radius=15)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Create icon label
        icon_label = ctk.CTkLabel(main_frame, text="⏱️", font=ctk.CTkFont(size=34))
        icon_label.pack(pady=(15, 5))
        
        # Create countdown label
        self.countdown_label = ctk.CTkLabel(
            main_frame, 
            text=f"Typing will begin in {self.seconds} seconds...\nPosition your cursor where typing should start!",
            font=ctk.CTkFont(size=14),
            wraplength=340
        )
        self.countdown_label.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Create progress bar
        self.progress_bar = ctk.CTkProgressBar(main_frame, width=340)
        self.progress_bar.pack(pady=(0, 10), padx=10, fill="x")
        self.progress_bar.set(0)
        
        # Create cancel button
        self.cancel_button = ctk.CTkButton(
            main_frame,
            text="Cancel",
            width=100,
            fg_color="#FF5555",
            hover_color="#CC4444",
            command=self.cancel
        )
        self.cancel_button.pack(pady=(0, 10))
        
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda event: self.cancel())
        
        # Start countdown
        self.after(0, self.update_countdown)
    
    def update_countdown(self):
        if self.seconds <= 0 or self.cancelled:
            self.result = "Complete" if not self.cancelled else "Cancel"
            if self.callback:
                self.callback(self.result)
            self.destroy()
            return
        
        self.countdown_label.configure(
            text=f"Typing will begin in {self.seconds} seconds...\nPosition your cursor where typing should start!"
        )
        self.progress_bar.set(1 - (self.seconds / 5))
        self.seconds -= 1
        self.after(1000, self.update_countdown)
    
    def cancel(self):
        self.cancelled = True
        self.result = "Cancel"
        self.destroy()
    
    def get(self):
        return self.result

class VClassAITyperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VClass AI Typer")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Add icon if available
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
            if os.path.exists(icon_path):
                icon = Image.open(icon_path)
                photo = ctk.CTkImage(icon)
                self.root.iconphoto(True, photo)
        except Exception as e:
            logger.error(f"Failed to load icon: {e}")

        # Session state simulation
        self.session_state = {
            "processing_status": None,
            "result": None,
            "file_info": None,
            "screenshots": [],
            "model_name": "google-gla:gemini-2.0-flash",
            "show_dialog": False,
        }

        # For storing the uploaded file path
        self.uploaded_file_path = None
        
        # Dialog control variables
        self.dialog_running = False
        self.countdown_dialog = None

        # Initialize UI
        self.setup_ui()

    def setup_ui(self):
        # Configure grid for better responsiveness
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.main_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        
        # Configure grid for main frame
        self.main_frame.grid_columnconfigure(1, weight=4)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self.main_frame, width=250, corner_radius=15)
        self.sidebar.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        
        # Content area
        self.content_frame = ctk.CTkFrame(self.main_frame, corner_radius=15)
        self.content_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        
        self.setup_sidebar()
        self.setup_content()

    def setup_sidebar(self):
        # Configure grid for sidebar
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(5, weight=1)  # Make the space above the reset button expandable
        
        # App header
        header_frame = ctk.CTkFrame(self.sidebar, corner_radius=10, fg_color="#1E1E2E")
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        # Style logo text
        ctk.CTkLabel(
            header_frame, 
            text="VClass AI Typer", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FFFFFF"
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            header_frame, 
            text="Document Automation Made Simple", 
            font=ctk.CTkFont(size=12),
            text_color="#D0D0D0",
            wraplength=230
        ).pack(pady=(0, 10))
        
        # API settings section
        api_frame = ctk.CTkFrame(self.sidebar, corner_radius=10)
        api_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            api_frame, 
            text="API Settings", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Provider selection
        self.provider_var = ctk.StringVar(value="Google")
        provider_menu = ctk.CTkOptionMenu(
            api_frame, 
            values=["Google", "OpenRouter", "Groq", "Claude"], 
            variable=self.provider_var,
            width=200,
            dynamic_resizing=False,
            font=ctk.CTkFont(size=13)
        )
        provider_menu.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # API key entry
        self.api_key_entry = ctk.CTkEntry(
            api_frame, 
            placeholder_text="Enter API Key", 
            show="•",
            width=200,
            font=ctk.CTkFont(size=13)
        )
        self.api_key_entry.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.api_key_entry.bind("<Return>", self.set_api_key)
        
        # Save API key button
        save_api_btn = ctk.CTkButton(
            api_frame, 
            text="Save API Key", 
            command=lambda: self.set_api_key(),
            font=ctk.CTkFont(size=13),
            height=32
        )
        save_api_btn.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        # Model selection
        self.model_options = [
            "google-gla:gemini-1.5-flash", 
            "google-gla:gemini-2.0-flash", 
            "groq:llama3-70b-8192", 
            "mistral:mistral-large-latest"
        ]
        self.model_var = ctk.StringVar(value=self.model_options[1])  # Default to gemini-2.0-flash
        model_menu = ctk.CTkOptionMenu(
            api_frame, 
            values=self.model_options, 
            variable=self.model_var,
            command=lambda x: self.set_model(x),
            width=200,
            dynamic_resizing=False,
            font=ctk.CTkFont(size=13)
        )
        model_menu.grid(row=4, column=0, padx=10, pady=(5, 10), sticky="ew")
        
        # Advanced settings section
        advanced_frame = ctk.CTkFrame(self.sidebar, corner_radius=10)
        advanced_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            advanced_frame, 
            text="Advanced Settings", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Typing speed
        typing_speed_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        typing_speed_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(
            typing_speed_frame, 
            text="Typing Speed:", 
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=0, sticky="w")
        
        self.speed_var = ctk.StringVar(value="0.03")
        self.typing_speed_var = ctk.DoubleVar(value=0.03)
        
        typing_speed_slider = ctk.CTkSlider(
            typing_speed_frame, 
            from_=0.001, 
            to=0.1, 
            variable=self.typing_speed_var,
            command=lambda val: self.speed_var.set(f"{val:.3f}s")
        )
        typing_speed_slider.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        
        speed_label = ctk.CTkLabel(
            typing_speed_frame, 
            textvariable=self.speed_var,
            font=ctk.CTkFont(size=12)
        )
        speed_label.grid(row=1, column=1, padx=(5, 0), pady=(0, 5))
        
        # Chunk size
        chunk_size_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        chunk_size_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(
            chunk_size_frame, 
            text="Chunk Size:", 
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=0, sticky="w")
        
        self.size_var = ctk.StringVar(value="2000")
        self.chunk_size_var = ctk.IntVar(value=2000)
        
        chunk_size_slider = ctk.CTkSlider(
            chunk_size_frame, 
            from_=500, 
            to=10000, 
            variable=self.chunk_size_var,
            command=lambda val: self.size_var.set(f"{int(val)}")
        )
        chunk_size_slider.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        
        size_label = ctk.CTkLabel(
            chunk_size_frame, 
            textvariable=self.size_var,
            font=ctk.CTkFont(size=12)
        )
        size_label.grid(row=1, column=1, padx=(5, 0), pady=(0, 5))
        
        # Checkboxes for options
        options_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        options_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="ew")
        
        self.headless_var = ctk.BooleanVar(value=True)
        headless_check = ctk.CTkCheckBox(
            options_frame, 
            text="Headless Mode", 
            variable=self.headless_var,
            font=ctk.CTkFont(size=13)
        )
        headless_check.grid(row=0, column=0, sticky="w", pady=2)
        
        self.screenshot_var = ctk.BooleanVar(value=True)
        screenshot_check = ctk.CTkCheckBox(
            options_frame, 
            text="Capture Screenshots", 
            variable=self.screenshot_var,
            font=ctk.CTkFont(size=13)
        )
        screenshot_check.grid(row=1, column=0, sticky="w", pady=2)
        
        # Expandable space
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.grid(row=3, column=0, sticky="ew")
        
        # Documentation section
        docs_frame = ctk.CTkFrame(self.sidebar, corner_radius=10, fg_color="#1A3A5A")
        docs_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(
            docs_frame, 
            text="Need Help?", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FFFFFF"
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            docs_frame, 
            text="Check our documentation for guides and troubleshooting tips.", 
            font=ctk.CTkFont(size=12),
            text_color="#D0D0D0",
            wraplength=220
        ).pack(anchor="w", padx=10, pady=(0, 5))
        
        docs_button = ctk.CTkButton(
            docs_frame, 
            text="View Documentation", 
            command=lambda: print("Documentation Clicked"),
            font=ctk.CTkFont(size=13),
            fg_color="#2F5D8A",
            hover_color="#3A6FA0"
        )
        docs_button.pack(padx=10, pady=(0, 10), fill="x")
        
        # Reset button
        reset_button = ctk.CTkButton(
            self.sidebar, 
            text="Reset Session", 
            command=self.reset_session,
            fg_color="#FF5555",
            hover_color="#CC4444",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        reset_button.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="sew")
        
        # Footer
        footer_label = ctk.CTkLabel(
            self.sidebar, 
            text="© 2025 No Data Stored", 
            font=ctk.CTkFont(size=10),
            text_color="#888888"
        )
        footer_label.grid(row=6, column=0, pady=(0, 5))

    def setup_content(self):
        # Configure grid for content frame
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
        
        # Tab view
        self.tab_view = ctk.CTkTabview(self.content_frame, corner_radius=10)
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Add tabs
        self.tab_view.add("Typer Agent")
        self.tab_view.add("Automation")
        self.tab_view.add("Support Us")
        self.tab_view.add("Settings")
        
        # Style the tabs
        self.tab_view.configure(
            segmented_button_fg_color="#2B2B2B",
            segmented_button_selected_color="#3B8ED0",
            segmented_button_selected_hover_color="#36719F",
            segmented_button_unselected_color="#2B2B2B",
            segmented_button_unselected_hover_color="#1F1F1F",
            text_color="#FFFFFF",
            text_color_disabled="#888888"
        )
        
        # Setup each tab
        self.setup_typer_tab()
        self.setup_automation_tab()
        self.setup_support_tab()
        self.setup_settings_tab()
        
        # Status bar
        status_frame = ctk.CTkFrame(self.content_frame, height=25, corner_radius=8)
        status_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            status_frame, 
            text="Ready", 
            font=ctk.CTkFont(size=12),
            text_color="#AAAAAA"
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=2, sticky="w")

    def setup_typer_tab(self):
        typer_tab = self.tab_view.tab("Typer Agent")
        typer_tab.grid_columnconfigure(0, weight=1)
        typer_tab.grid_rowconfigure(4, weight=1)
        
        # Upload section
        upload_frame = ctk.CTkFrame(typer_tab, corner_radius=10)
        upload_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        upload_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            upload_frame, 
            text="Document Selection", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="w")
        
        # File selection
        ctk.CTkLabel(
            upload_frame, 
            text="Select Document:", 
            font=ctk.CTkFont(size=14)
        ).grid(row=1, column=0, padx=15, pady=(15, 5), sticky="w")
        
        self.file_button = ctk.CTkButton(
            upload_frame, 
            text="Choose File", 
            command=self.upload_file,
            width=150,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        self.file_button.grid(row=1, column=1, padx=15, pady=(15, 5), sticky="e")
        
        self.file_label = ctk.CTkLabel(
            upload_frame, 
            text="No file selected", 
            font=ctk.CTkFont(size=13),
            wraplength=400
        )
        self.file_label.grid(row=2, column=0, columnspan=2, padx=15, pady=(5, 15), sticky="w")
        
        # Actions section
        action_frame = ctk.CTkFrame(typer_tab, corner_radius=10)
        action_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        action_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            action_frame, 
            text="Document Actions", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        # Start button with nice styling
        self.start_button = ctk.CTkButton(
            action_frame, 
            text="Start AI Typer", 
            state="disabled", 
            command=self.start_typing,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2AAA8A",
            hover_color="#1D8870"
        )
        self.start_button.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        
        # Progress bar with percentage
        progress_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        progress_frame.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="ew")
        
        progress_frame.grid_columnconfigure(0, weight=1)
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=5)
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            progress_frame, 
            text="0%", 
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.grid(row=1, column=0, sticky="e")
        
        # Document preview section
        preview_frame = ctk.CTkFrame(typer_tab, corner_radius=10)
        preview_frame.grid(row=4, column=0, padx=10, pady=(5, 10), sticky="nsew")
        
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            preview_frame, 
            text="Document Preview", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        self.preview_text = ctk.CTkTextbox(
            preview_frame, 
            state="disabled",
            font=ctk.CTkFont(size=13, family="Consolas")
        )
        self.preview_text.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="nsew")

    def setup_automation_tab(self):
        automation_tab = self.tab_view.tab("Automation")
        automation_tab.grid_columnconfigure(0, weight=1)
        automation_tab.grid_rowconfigure(0, weight=1)
        
        # Coming soon frame
        coming_soon_frame = ctk.CTkFrame(automation_tab, corner_radius=15)
        coming_soon_frame.grid(padx=20, pady=20, sticky="nsew")
        
        coming_soon_frame.grid_columnconfigure(0, weight=1)
        coming_soon_frame.grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(
            coming_soon_frame, 
            text="Automation Features", 
            font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(30, 10))
        
        ctk.CTkLabel(
            coming_soon_frame, 
            text="Coming Soon", 
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#3B8ED0"
        ).grid(row=1, column=0, padx=20, pady=10)
        
        ctk.CTkLabel(
            coming_soon_frame, 
            text="We're working on exciting new automation features\nto help you with repetitive document tasks.\nStay tuned for updates!", 
            font=ctk.CTkFont(size=14),
            wraplength=400
        ).grid(row=2, column=0, padx=20, pady=(10, 30))

    def setup_support_tab(self):
        support_tab = self.tab_view.tab("Support Us")
        support_tab.grid_columnconfigure(0, weight=1)
        support_tab.grid_rowconfigure(0, weight=1)
        
        # Support frame
        support_frame = ctk.CTkFrame(support_tab, corner_radius=15)
        support_frame.grid(padx=20, pady=20, sticky="nsew")
        
        support_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            support_frame, 
            text="Support Our Work", 
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(30, 15))
        
        ctk.CTkLabel(
            support_frame, 
            text="Your support helps us continue developing and improving VClass AI Typer.",
            font=ctk.CTkFont(size=14),
            wraplength=450
        ).pack(pady=(0, 20))
        
        # Support options
        options_frame = ctk.CTkFrame(support_frame, fg_color="transparent")
        options_frame.pack(pady=10, padx=20, fill="x")
        
        # Patreon button
        patreon_btn = ctk.CTkButton(
            options_frame, 
            text="Support on Patreon", 
            command=lambda: print("Patreon clicked"),
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#FF424D",
            hover_color="#E6323D"
        )
        patreon_btn.pack(pady=10, fill="x")
        
        # PayPal button
        paypal_btn = ctk.CTkButton(
            options_frame, 
            text="Donate via PayPal", 
            command=lambda: print("PayPal clicked"),
            height=45, 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0070BA",
            hover_color="#005998"
        )
        paypal_btn.pack(pady=10, fill="x")
        
        # Binance button
        binance_btn = ctk.CTkButton(
            options_frame, 
            text="Crypto via Binance", 
            command=lambda: print("Binance clicked"),
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#F0B90B",  # Binance yellow
            hover_color="#D9A70A",
            text_color="#000000"
        )
        binance_btn.pack(pady=10, fill="x")
        
        # Thank you message
        ctk.CTkLabel(
            support_frame, 
            text="Thank you for supporting independent development!",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#3B8ED0"
        ).pack(pady=(20, 30))

    def setup_settings_tab(self):
        settings_tab = self.tab_view.tab("Settings")
        settings_tab.grid_columnconfigure(0, weight=1)
        settings_tab.grid_rowconfigure(0, weight=1)
        
        # Settings frame
        settings_frame = ctk.CTkFrame(settings_tab, corner_radius=15)
        settings_frame.grid(padx=20, pady=20, sticky="nsew")
        
        settings_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            settings_frame, 
            text="Settings Guide", 
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(30, 20))
        
        # Create scrollable frame for settings
        scrollable_frame = ctk.CTkScrollableFrame(settings_frame)
        scrollable_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Add settings guide sections
        self.add_settings_section(
            scrollable_frame,
            "API Configuration", 
            "Set up your preferred AI model provider and API key. Your API keys are stored locally and are never transmitted to our servers.",
            "#1A3A5A"
        )
        
        self.add_settings_section(
            scrollable_frame,
            "Typing Speed", 
            "Adjust how fast the AI types. Lower values result in faster typing, while higher values create more human-like typing patterns.",
            "#2A3A2A"
        )
        
        self.add_settings_section(
            scrollable_frame,
            "Chunk Size", 
            "Control how much text is processed at once. Larger chunks may improve speed but might require more memory and processing power.",
            "#3A2A2A"
        )
        
        self.add_settings_section(
            scrollable_frame,
            "Headless Mode", 
            "When enabled, processing happens in the background without showing visual feedback. This can improve performance on slower systems.",
            "#2A2A3A"
        )
        
        self.add_settings_section(
            scrollable_frame,
            "Screenshot Capture", 
            "Capture screenshots during the typing process for monitoring and troubleshooting purposes.",
            "#2A3A3A"
        )

    def add_settings_section(self, parent, title, description, bg_color):
        section_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color=bg_color)
        section_frame.pack(pady=10, fill="x")
        
        ctk.CTkLabel(
            section_frame, 
            text=title, 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FFFFFF"
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(
            section_frame, 
            text=description, 
            font=ctk.CTkFont(size=13),
            text_color="#D0D0D0",
            wraplength=550,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))

    def set_api_key(self, event=None):
        provider = self.provider_var.get()
        api_key = self.api_key_entry.get()
        if api_key:
            env_var_map = {
                "Google": "GOOGLE_API_KEY",
                "OpenRouter": "OPENAI_API_KEY",
                "Groq": "GROQ_API_KEY",
                "Claude": "ANTHOPIC_API_KEY",
            }
            os.environ[env_var_map[provider]] = api_key
            self.status_label.configure(text=f"API Key Set for {provider}")
            
            # Show custom success dialog
            CustomDialog(
                self.root,
                title="API Key Saved",
                message=f"Your {provider} API key has been saved successfully.",
                icon="check",
                buttons=["OK"],
                width=350,
                height=180
            )

    def set_model(self, model):
        self.session_state["model_name"] = model
        self.status_label.configure(text=f"Model: {model}")

    def upload_file(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("Document files", "*.docx *.odt *.pdf")])
        if file_path:
            self.uploaded_file_path = file_path
            file_name = os.path.basename(file_path)
            
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            uploaded_file = UploadedFile(file_name, file_bytes)
            
            self.file_label.configure(text=f"Selected: {file_name}")
            self.start_button.configure(state="normal")
            self.validate_and_preview(uploaded_file)

    def validate_and_preview(self, uploaded_file):
        is_valid, validation_result = is_valid_doc(uploaded_file)
        if not is_valid:
            self.status_label.configure(text=f"Invalid document: {validation_result}")
            self.start_button.configure(state="disabled")
            
            # Use custom dialog instead of CTkMessagebox
            CustomDialog(
                self.root,
                title="Invalid Document",
                message=f"Invalid document: {validation_result}",
                icon="cancel",
                buttons=["OK"],
                width=400,
                height=200
            )
        else:
            self.session_state["file_info"] = validation_result
            try:
                file_content = extract_file_content(uploaded_file, validation_result)
                self.preview_text.configure(state="normal")
                self.preview_text.delete("1.0", "end")
                self.preview_text.insert("1.0", file_content[:1000])
                if len(file_content) > 1000:
                    self.preview_text.insert("end", "\n\n... (preview limited to 1000 characters)")
                self.preview_text.configure(state="disabled")
                self.status_label.configure(text=f"Valid {validation_result['type'].upper()} file")
                
                # Use custom dialog instead of CTkMessagebox
                CustomDialog(
                    self.root,
                    title="Document Validated",
                    message=f"Valid {validation_result['type'].upper()} file detected: {uploaded_file.name}",
                    icon="check",
                    buttons=["OK"],
                    width=400,
                    height=200
                )
            except Exception as e:
                self.status_label.configure(text=f"Error: {str(e)}")
                logger.error(f"Preview error: {str(e)}")
                
                # Use custom dialog instead of CTkMessagebox
                CustomDialog(
                    self.root,
                    title="Error",
                    message=f"Error processing document: {str(e)}",
                    icon="cancel",
                    buttons=["OK"],
                    width=400,
                    height=200
                )

    async def process_document(self, doc_path, delay, error_correction):
        try:
            retyper = DocumentRetyper(delay=delay, model_name=self.session_state["model_name"])
            await retyper.async_init()

            doc_info = await retyper.display_document_info(doc_path)
            char_count_match = re.search(r'(\d+) characters', doc_info)
            total_chars = int(char_count_match.group(1)) if char_count_match else 1000

            if doc_path.endswith('.docx'):
                document_text = extract_text_from_docx(doc_path)
            else:
                with open(doc_path, 'r', encoding='utf-8', errors='ignore') as f:
                    document_text = f.read()

            # We'll handle the countdown dialog in the start_typing method
            # to avoid cascading dialogs
            
            mouse = MouseController()
            cursor_position = mouse.position

            # Alert user that typing is starting
            self.status_label.configure(text="Typing in progress... Don't move cursor!")
            
            # Use the new method retype_document_for_ctk
            retyped_content = await retyper.retype_document_for_ctk(
                document_text,
                cursor_position,
                error_correction
            )

            # Simulate progress updates
            self.progress_bar.set(0)
            for i in range(1, 101):
                progress = i / 100
                self.progress_bar.set(progress)
                self.progress_label.configure(text=f"{int(progress * 100)}%")
                self.status_label.configure(text=f"Typing: {int(progress * total_chars)}/{total_chars} chars ({int(progress*100)}%)")
                await asyncio.sleep(0.05)

            self.progress_bar.set(1.0)
            self.progress_label.configure(text="100%")
            self.status_label.configure(text="Typing completed successfully!")
            
            # Show completion dialog
            await asyncio.sleep(0.5)  # Small delay before showing completion dialog
            self.root.after(0, lambda: CustomDialog(
                self.root,
                title="Typing Completed",
                message="Your document has been successfully typed!",
                icon="check",
                buttons=["OK"],
                width=400,
                height=200
            ))
            
            return retyped_content

        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
            logger.error(f"Typing error: {str(e)}")
            
            self.root.after(0, lambda: CustomDialog(
                self.root,
                title="Typing Error",
                message=f"An error occurred during typing:\n{str(e)}",
                icon="cancel",
                buttons=["OK"],
                width=400,
                height=250
            ))
            return None

    def countdown_completed(self, result):
        if result == "Cancel":
            self.status_label.configure(text="Typing cancelled by user.")
            self.start_button.configure(state="normal")
            return
        
        # Continue with the typing process
        self.start_typing_process()

    def start_typing(self):
        if not self.uploaded_file_path:
            CustomDialog(
                self.root,
                title="No Document",
                message="Please upload a document first.",
                icon="warning",
                buttons=["OK"],
                width=350,
                height=180
            )
            return
        
        # Disable start button to prevent multiple clicks
        self.start_button.configure(state="disabled")
        
        # Show countdown dialog
        self.countdown_dialog = CountdownDialog(
            self.root, 
            seconds=5, 
            callback=self.countdown_completed
        )

    def start_typing_process(self):
        self.session_state["processing_status"] = "started"
        
        # Show "Get Ready" dialog
        ready_dialog = CustomDialog(
            self.root,
            title="Prepare for Typing",
            message="Position your cursor where typing should start.\nDon't move your mouse or keyboard during the process.",
            icon="warning",
            buttons=["Start Now", "Cancel"],
            default_button="Start Now",
            cancel_button="Cancel",
            width=450,
            height=220
        )
        
        if ready_dialog.get() == "Cancel":
            self.status_label.configure(text="Typing cancelled by user.")
            self.start_button.configure(state="normal")
            return
        
        # Continue with the typing process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(self.uploaded_file_path)[1]) as tmp_file:
                with open(self.uploaded_file_path, 'rb') as src_file:
                    tmp_file.write(src_file.read())
                temp_path = tmp_file.name
            result = loop.run_until_complete(self.process_document(temp_path, self.typing_speed_var.get(), True))
            self.session_state["result"] = {"success": bool(result), "message": "Document processed"}
        finally:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            loop.close()
            self.start_button.configure(state="normal")

    def reset_session(self):
        # Ask for confirmation
        confirm_dialog = CustomDialog(
            self.root,
            title="Confirm Reset",
            message="Are you sure you want to reset the current session?\nThis will clear all loaded documents and progress.",
            icon="question",
            buttons=["Reset", "Cancel"],
            default_button="Cancel",
            cancel_button="Cancel",
            width=400,
            height=220
        )
        
        if confirm_dialog.get() != "Reset":
            return
        
        # Reset the session
        self.session_state = {
            "processing_status": None,
            "result": None,
            "file_info": None,
            "screenshots": [],
            "model_name": "google-gla:gemini-2.0-flash",
            "show_dialog": False,
        }
        self.uploaded_file_path = None
        self.file_label.configure(text="No file selected")
        self.start_button.configure(state="disabled")
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.configure(state="disabled")
        self.status_label.configure(text="Session reset")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        
        # Show reset complete dialog
        CustomDialog(
            self.root,
            title="Reset Complete",
            message="Session has been reset successfully.",
            icon="check",
            buttons=["OK"],
            width=350,
            height=180
        )

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = ctk.CTk()
    app = VClassAITyperApp(root)
    app.run()