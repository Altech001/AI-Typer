import os
import re
import tempfile
import customtkinter as ctk
from PIL import Image
import asyncio
import logging
import threading
from pathlib import Path
from pynput.mouse import Controller as MouseController
from CTkMessagebox import CTkMessagebox
from utils import extract_file_content, is_valid_doc, display_screenshots
from typer import DocumentRetyper, extract_text_from_docx
from validation import display_error_details
from analzyer import analyze_docx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Customtkinter appearance
ctk.set_appearance_mode("Light")
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

class VClassAITyperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Typer")
        self.root.geometry("1000x700")
        self.root.minsize(700, 500)

        # Session state simulation
        self.session_state = {
            "processing_status": None,
            "result": None,
            "file_info": None,
            "screenshots": [],
            "model_name": "google-gla:gemini-2.0-flash",
            "show_dialog": False,
        }
        
        self.uploaded_file_path = None
        self.typing_in_progress = False
        self.countdown_running = False
        self.cancel_button = None

        # Initialize UI
        self.setup_ui()

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.sidebar = ctk.CTkFrame(self.main_frame, width=250, corner_radius=10)
        self.sidebar.pack(side="left", fill="y", padx=(0, 5))

        self.setup_sidebar()

        self.content_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        self.tab_view = ctk.CTkTabview(self.content_frame, corner_radius=10)
        self.tab_view.pack(pady=10, padx=10, fill="both", expand=True)

        self.tab_view.add("Typer Agent")
        self.tab_view.add("Automation")
        self.tab_view.add("Support Us")
        self.tab_view.add("Settings")

        self.setup_tabs()

    def setup_sidebar(self):
        self.header_frame = ctk.CTkFrame(self.sidebar, corner_radius=5)
        self.header_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.header_frame, text="AI Typer Agent", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 5))
        ctk.CTkLabel(self.header_frame, text="Automate document typing with ease", font=ctk.CTkFont(size=12), wraplength=230).pack()

        self.api_frame = ctk.CTkFrame(self.sidebar, corner_radius=5)
        self.api_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.api_frame, text="API Preferences", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=5)

        self.provider_var = ctk.StringVar(value="Google")
        ctk.CTkOptionMenu(self.api_frame, values=["Google", "OpenRouter", "Groq", "Claude"], variable=self.provider_var).pack(pady=5, padx=5, fill="x")

        self.api_key_entry = ctk.CTkEntry(self.api_frame, placeholder_text="Enter API Key", show="*")
        self.api_key_entry.pack(pady=5, padx=5, fill="x")
        self.api_key_entry.bind("<Return>", self.set_api_key)

        self.model_options = [
            "google-gla:gemini-1.5-flash", "google-gla:gemini-2.0-flash", "groq:llama3-70b-8192", "mistral:mistral-large-latest"
        ]
        self.model_var = ctk.StringVar(value=self.model_options[0])
        ctk.CTkOptionMenu(self.api_frame, values=self.model_options, variable=self.model_var, command=lambda x: self.set_model(x)).pack(pady=5, padx=5, fill="x")

        self.advanced_frame = ctk.CTkFrame(self.sidebar, corner_radius=5)
        self.advanced_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.advanced_frame, text="Advanced Settings", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=5)

        self.typing_speed_var = ctk.DoubleVar(value=0.03)
        self.typing_speed_slider = ctk.CTkSlider(self.advanced_frame, from_=0.001, to=0.1, variable=self.typing_speed_var, number_of_steps=99, command=self.update_typing_speed_label)
        self.typing_speed_slider.pack(pady=5, padx=5, fill="x")
        
        self.typing_speed_label = ctk.CTkLabel(self.advanced_frame, text=f"Typing Speed: {self.typing_speed_var.get():.3f}s")
        self.typing_speed_label.pack()

        self.chunk_size_var = ctk.IntVar(value=2000)
        self.chunk_size_slider = ctk.CTkSlider(self.advanced_frame, from_=500, to=10000, variable=self.chunk_size_var, number_of_steps=95, command=self.update_chunk_size_label)
        self.chunk_size_slider.pack(pady=5, padx=5, fill="x")
        
        self.chunk_size_label = ctk.CTkLabel(self.advanced_frame, text=f"Chunk Size: {self.chunk_size_var.get()}")
        self.chunk_size_label.pack()

        self.headless_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.advanced_frame, text="Headless Mode", variable=self.headless_var).pack(pady=5, anchor="w", padx=5)

        self.screenshot_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.advanced_frame, text="Capture Screenshots", variable=self.screenshot_var).pack(pady=5, anchor="w", padx=5)

        ctk.CTkButton(self.sidebar, text="Reset Session", command=self.reset_session, fg_color="#FF5555", hover_color="#CC4444").pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(self.sidebar, text="© 2025 No Data Stored", font=ctk.CTkFont(size=10)).pack(side="bottom", pady=5)

    def update_typing_speed_label(self, value=None):
        self.typing_speed_label.configure(text=f"Typing Speed: {self.typing_speed_var.get():.3f}s")
        
    def update_chunk_size_label(self, value=None):
        self.chunk_size_label.configure(text=f"Chunk Size: {self.chunk_size_var.get()}")

    def setup_tabs(self):
        typer_tab = self.tab_view.tab("Typer Agent")
        typer_frame = ctk.CTkFrame(typer_tab, corner_radius=5)
        typer_frame.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(typer_frame, text="Upload Your Document", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=5)
        self.file_button = ctk.CTkButton(typer_frame, text="Choose File", command=self.upload_file)
        self.file_button.pack(pady=5, fill="x")

        self.file_label = ctk.CTkLabel(typer_frame, text="No file selected", font=ctk.CTkFont(size=12))
        self.file_label.pack(pady=5)

        self.start_button = ctk.CTkButton(typer_frame, text="Start AI Typer", state="disabled", command=self.start_typing)
        self.start_button.pack(pady=10, fill="x")
        
        self.countdown_label = ctk.CTkLabel(typer_frame, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.countdown_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(typer_frame)
        self.progress_bar.pack(pady=5, fill="x")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(typer_frame, text="Ready", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=5)

        self.preview_frame = ctk.CTkFrame(typer_frame, corner_radius=5)
        self.preview_frame.pack(pady=10, fill="both", expand=True)
        ctk.CTkLabel(self.preview_frame, text="Document Preview", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=5)
        self.preview_text = ctk.CTkTextbox(self.preview_frame, height=150, state="disabled")
        self.preview_text.pack(pady=5, padx=5, fill="both", expand=True)

        automation_tab = self.tab_view.tab("Automation")
        automation_frame = ctk.CTkFrame(automation_tab, corner_radius=5)
        automation_frame.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkLabel(automation_frame, text="Automation - Coming Soon", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkLabel(automation_frame, text="Stay tuned for exciting updates!", font=ctk.CTkFont(size=12)).pack()

        support_tab = self.tab_view.tab("Support Us")
        support_frame = ctk.CTkFrame(support_tab, corner_radius=5)
        support_frame.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkLabel(support_frame, text="Support Our Work", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkLabel(support_frame, text="Contribute via Patreon, Binance, or PayPal.", font=ctk.CTkFont(size=12)).pack()

        settings_tab = self.tab_view.tab("Settings")
        settings_frame = ctk.CTkFrame(settings_tab, corner_radius=5)
        settings_frame.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkLabel(settings_frame, text="Settings Guide", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkLabel(settings_frame, text="Configure typing speed, chunk size, and more.", font=ctk.CTkFont(size=12)).pack()

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
            self.status_label.configure(text="API Key Set")

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
            CTkMessagebox(
                title="Invalid Document",
                message=f"Invalid document: {validation_result}",
                icon="cancel",
                option_1="OK"
            )
        else:
            self.session_state["file_info"] = validation_result
            try:
                file_content = extract_file_content(uploaded_file, validation_result)
                self.preview_text.configure(state="normal")
                self.preview_text.delete("1.0", "end")
                self.preview_text.insert("1.0", file_content[:1000])
                self.preview_text.configure(state="disabled")
                self.status_label.configure(text=f"Valid {validation_result['type'].upper()} file")
                CTkMessagebox(
                    title="Document Validated",
                    message=f"Valid {validation_result['type'].upper()} file detected: {uploaded_file.name}",
                    icon="check",
                    option_1="OK"
                )
            except Exception as e:
                self.status_label.configure(text=f"Error: {str(e)}")
                logger.error(f"Preview error: {str(e)}")
                CTkMessagebox(
                    title="Error",
                    message=f"Error processing document: {str(e)}",
                    icon="cancel",
                    option_1="OK"
                )

    async def update_countdown(self, seconds):
        self.countdown_running = True
        for i in range(seconds, 0, -1):
            if not self.countdown_running:
                break
            self.countdown_label.configure(text=f"Typing starts in {i} seconds... Position your cursor!")
            await asyncio.sleep(1)
        self.countdown_label.configure(text="")
        self.countdown_running = False

    def cancel_countdown(self):
        self.countdown_running = False
        self.status_label.configure(text="Typing cancelled by user.")
        self.start_button.configure(state="normal")
        if self.cancel_button:
            self.cancel_button.destroy()

    async def process_document(self, doc_path, delay, error_correction):
        try:
            logger.info("Initializing DocumentRetyper...")
            retyper = DocumentRetyper(delay=delay, model_name=self.session_state["model_name"])
            await retyper.async_init()

            logger.info("Displaying document info...")
            doc_info = await retyper.display_document_info(doc_path)
            char_count_match = re.search(r'(\d+) characters', doc_info)
            total_chars = int(char_count_match.group(1)) if char_count_match else 1000
            logger.info(f"Total characters in document: {total_chars}")

            if doc_path.endswith('.docx'):
                document_text = extract_text_from_docx(doc_path)
            else:
                with open(doc_path, 'r', encoding='utf-8', errors='ignore') as f:
                    document_text = f.read()

            # Single dialog box with countdown information
            typing_dialog = CTkMessagebox(
                title="Prepare for Typing",
                message="Open a text editor (e.g., Notepad) and click where you want typing to start.\n\nWhen ready, click OK to begin the 5-second countdown.\nTyping will begin automatically when countdown finishes.",
                icon="info",
                option_1="OK",
                option_2="Cancel"
            )
            
            result = typing_dialog.get()
            if result == "Cancel":
                self.status_label.configure(text="Typing cancelled by user.")
                return None
                
            # Start countdown in the main UI
            await self.update_countdown(5)
            
            if not self.countdown_running:  # User cancelled
                return None

            mouse = MouseController()
            cursor_position = mouse.position
            logger.info(f"Cursor position captured: {cursor_position}")

            # Alert user that typing is starting
            self.status_label.configure(text="Typing in progress... Don't move cursor!")
            self.typing_in_progress = True

            # Use the new method retype_document_for_ctk
            logger.info("Starting retype_document_for_ctk...")
            retyped_content = await retyper.retype_document_for_ctk(
                document_text,
                cursor_position,
                error_correction
            )
            logger.info("retype_document_for_ctk completed.")

            # Simulate progress updates (since we can't track real-time progress)
            for i in range(1, 101):
                if not self.typing_in_progress:
                    break  # Exit if typing was cancelled
                progress = i / 100
                chars_typed = int(progress * total_chars)
                self.root.after(0, lambda: self.progress_bar.set(progress))
                self.root.after(0, lambda: self.status_label.configure(text=f"Typing: {chars_typed}/{total_chars} chars ({int(progress*100)}%)"))
                await asyncio.sleep(0.05)

            if self.typing_in_progress:  # Only if not cancelled
                self.root.after(0, lambda: self.progress_bar.set(1.0))
                self.root.after(0, lambda: self.status_label.configure(text="Typing completed successfully!"))
                
                # Show a single completion dialog
                self.root.after(0, lambda: CTkMessagebox(
                    title="Typing Completed",
                    message="Your document has been successfully typed!",
                    icon="check",
                    option_1="OK"
                ).get())
            
            return retyped_content

        except Exception as e:
            logger.error(f"Typing error: {str(e)}")
            self.root.after(0, lambda: self.status_label.configure(text=f"Error: {str(e)}"))
            self.root.after(0, lambda: CTkMessagebox(
                title="Typing Error",
                message=f"An error occurred during typing:\n{str(e)}",
                icon="cancel",
                option_1="OK"
            ).get())
            return None
        finally:
            self.typing_in_progress = False
            if self.cancel_button:
                self.root.after(0, lambda: self.cancel_button.destroy())

    def start_typing(self):
        if not self.uploaded_file_path:
            CTkMessagebox(
                title="No Document",
                message="Please upload a document first.",
                icon="warning",
                option_1="OK"
            )
            return

        # Create cancel button that appears during typing
        self.cancel_button = ctk.CTkButton(
            self.tab_view.tab("Typer Agent"), 
            text="Cancel Typing", 
            command=self.cancel_typing,
            fg_color="#FF5555", 
            hover_color="#CC4444"
        )
        self.cancel_button.pack(pady=5, padx=10, fill="x")
        
        self.session_state["processing_status"] = "started"
        self.start_button.configure(state="disabled")
        self.typing_in_progress = True

        # Run the async task in a separate thread
        def run_async_task():
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
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                loop.close()
                self.root.after(0, lambda: self.start_button.configure(state="normal"))

        # Start the async task in a separate thread
        threading.Thread(target=run_async_task, daemon=True).start()

    def cancel_typing(self):
        """Cancel the typing process if it's in progress"""
        if self.typing_in_progress:
            self.typing_in_progress = False
        if self.countdown_running:
            self.cancel_countdown()
        self.status_label.configure(text="Typing cancelled by user")
        self.start_button.configure(state="normal")
        if self.cancel_button:
            self.cancel_button.destroy()

    def reset_session(self):
        if self.typing_in_progress:
            self.cancel_typing()
            
        self.session_state = {
            "processing_status": None,
            "result": None,
            "file_info": None,
            "screenshots": [],
            "model_name": "google-gla:gemini-2.0-flash",
            "show_dialog": False,
        }
        self.file_label.configure(text="No file selected")
        self.start_button.configure(state="disabled")
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.configure(state="disabled")
        self.status_label.configure(text="Session reset")
        self.countdown_label.configure(text="")
        self.progress_bar.set(0)
        self.uploaded_file_path = None
        CTkMessagebox(
            title="Reset Complete",
            message="Session has been reset successfully.",
            icon="check",
            option_1="OK"
        )

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = ctk.CTk()
    app = VClassAITyperApp(root)
    app.run()