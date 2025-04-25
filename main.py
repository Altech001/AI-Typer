import os
from pathlib import Path
import re
import tempfile
import streamlit as st
from utils import (
    extract_file_content,
    is_valid_doc,
    display_screenshots,
)
from typer import DocumentRetyper, extract_text_from_docx
from validation import (
    display_error_details
)
from pynput.mouse import Controller as MouseController
import asyncio
import logging
from analzyer import analyze_docx
import time  # Import time for delay
from batcher import BatchTyper  # Import the BatchTyper class
from pynput.keyboard import Controller, Key  # Import pynput for keyboard control

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="AI Typer",
    layout="centered",
    initial_sidebar_state="expanded",
    page_icon="🚀",
)

# Initialize session state
if 'processing_status' not in st.session_state:
    st.session_state.processing_status = None
if 'result' not in st.session_state:
    st.session_state.result = None
if 'file_info' not in st.session_state:
    st.session_state.file_info = None
if 'screenshots' not in st.session_state:
    st.session_state.screenshots = []

# Sidebar
with st.sidebar:
    st.title("AI Typer Agent")
    st.caption("This is an automation Tool that automates to type characters from the given document")
    st.header("Settings")
    
    st.subheader("API Preferences")
    with st.expander("Set Your Own API Keys", expanded=True):
        st.caption("You can easily set your API keys. With Faster Models")
        provider = st.selectbox("Choose Provider", ["Google", "OpenRouter", "Groq", "Claude"])
        api_key = st.text_input(f"Enter {provider} API Key", type="password")

        if api_key:
            env_var_map = {
                "Google": "GOOGLE_API_KEY",
                "OpenRouter": "OPENAI_API_KEY",
                "Groq": "GROQ_API_KEY",
                "Claude": "ANTHOPIC_API_KEY",
            }
            os.environ[env_var_map[provider]] = api_key

        model_options = [
            "google-gla:gemini-2.0-flash",
            "google-gla:gemini-1.5-flash",
            "google-gla:gemini-2.0-pro",
            "mistral:mistral-large-latest",
            "mistral-small-latest",
            "groq:llama3-70b-8192",
            "groq:deepseek-r1-distill-llama-70b",
            "groq:gemma2-9b-it",
            "groq:llama3-70b-8192",
            "groq:llama3-8b-8192",
            "groq:llama-3.3-70b-versatile",
            "groq:gemma2-9b-it",
            "groq:qwen-2.5-32b",
            "groq:mistral-saba-24b",
            "groq:deepseek-r1-distill-llama-70b",
            "groq:deepseek-r1-distill-qwen-32b",
            "groq:llama-3.2-11b-vision-preview",
            "groq:llama-3.2-90b-vision-preview",
            "groq:meta-llama/llama-4-maverick-17b-128e-instruct",
            "groq:meta-llama/llama-4-scout-17b-16e-instruct",
            "groq:qwen-2.5-coder-32b",
            "groq:qwen-qwq-32b",
            "groq:allam-2-7b",
        ]
        selected_model = st.selectbox("Choose an AI Model", model_options)
        st.session_state.model_name = selected_model

    st.caption("### Keep Your Credentials Safe and also Don't Set what you don't know")
    st.caption("Configure your preferences and automation reset settings here.")
    
    st.subheader("Anonymous Credentials")
    reg_number = st.text_input("Rank Number", help="Your are yet to reach for better")
    password = st.text_input("Hash Passcode", type="password", help="Your have to be ranked for the hash")
    
    st.subheader("Browser Settings")
    
    with st.expander("Advanced Cyber Speed", expanded=False):
        st.caption("Keep in Mind that the cyber speed will go wrong in accuary (65.5%)")
        typing_speed = st.slider(
            "Typing Speed (delay in seconds)",
            0.001,
            0.1,
            0.03,
            0.001,
            key="type_speed",
            help="Lower values result in faster typing"
        )
                
        chunk_size = st.slider(
            "Chunk Size for Large Documents",
            min_value=500,
            max_value=10000,
            value=2000,
            help="Characters per chunk when processing large documents"
        )
    
    with st.expander("More Options", expanded=False):
        st.markdown("### ⚙️ Additional Settings")
        st.markdown("""
        - **Headless Mode**: Run the browser in the background without a visible window.        
        - **Keep as Docx**: Retains the document in its original format for better compatibility.
        """)
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            headless_mode = st.checkbox(
                "Headless Mode🕶️ ",
                value=True,
                help="Run browser in background (no visible window)"
            )

        with col2:
            doc_type = st.selectbox(
                "📄 Document Type",
                options=["Docx / Word Document", "PDF", "TXT", "ODT"],
                help="Select the type of document you are uploading"
            )

    take_screenshots = st.checkbox(
        "Capture Screenshots",
        value=True,
        help="Take screenshots during the automation process"
    )
    
    if st.button("🔁 Reset Session"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

    st.markdown("---")
    st.write("📍 Powered by **Breakers** | Made with ❤️ in Uganda")
    st.write("📧 Contact: support@dontcall.com | 🌐 [anonymus.com](https://missi.com)")
    st.caption("© 2025 . No Data is Stored on this site. All data is processed locally.")

# Main Page
col1, col2 = st.columns([8, 2])

with col1:
    st.title("AI Breaker")

with col2:
    if st.button("💬", help="Show Info Dialog"):
        st.session_state.show_dialog = not st.session_state.get("show_dialog", False)

if st.session_state.get("show_dialog", False):
    with st.container():
        st.markdown("### 🗨️ Read with caution")
        st.info("""
        This application automates the process of typing documents into the VClass online editor.
        Upload your document, provide your credentials, and let the automation handle the rest.
        """)
        if st.button("❌ Close"):
            st.session_state.show_dialog = False

st.markdown("\n \n \n")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🔧 Typer Agent Document", "⚙️ Automation", "⭐ Support Us 💰💰", " ⚙️ Settings"])

with tab1:
    with st.expander("Learn To Use The Agent "):
        st.caption("""
        1. Upload a  .docx file using the file uploader
        2. Adjust typing speed if needed
        3. Open the target application where you want the text to be typed
        4. Click "Start AI Retyper"
        5. You'll have 5 seconds to position your cursor where typing should begin
        6. Stay still and let the typing complete
        """)
    st.markdown("### 📤 Upload Your Document")
    st.caption("""
    Drag and drop your document below or click **Browse Files**.  
    Supported formats: **.docx**, **.odt**, **.pdf**
    """)
    
    uploaded_file = st.file_uploader(
        label="",
        type=["docx", "odt", "pdf"],
        accept_multiple_files=False,
        help="Upload a document to process (Docx, ODT, PDF,C-Soon,)",
        label_visibility="collapsed"
    )
    
    st.caption("**Note:** Ensure your document is in a supported format and contains valid content.")

    if uploaded_file is not None:
        is_valid, validation_result = is_valid_doc(uploaded_file)
        
        if not is_valid:
            st.error(f"Invalid document: {validation_result}")
        else:
            st.session_state.file_info = validation_result
            
            try:
                file_content = extract_file_content(uploaded_file, validation_result)
                
                with st.expander("Preferences (Don't Change Anything) ", expanded=False):
                    st.caption("The lower (.001) the slider the faster the agent and the higher the slider the slower the agent")
                    st.caption("Default: 0.003 (Human Typing With Accuracy 85%)")
                    speed_options = {
                        "Lightning Flash": 0.001,  # Fastest, flash-like speed
                        "Super Fast": 0.003,      # Very fast, slightly smoother
                        "Fast": 0.007,            # Still quick but noticeable
                        "Medium": 0.015,          # Moderate, human-readable
                        "Slow": 0.03              # Slowest, for effect
                    }
                    typing_delay = st.slider(
                        "Typing Speed (delay in seconds)",
                        0.001,  # Minimum delay (very fast)
                        0.05,   # Maximum delay (still relatively fast)
                        0.01,   # Default value (faster than 0.03)
                        0.001,  # Step size (fine-grained control)
                        help="Lower values result in faster, flash-like typing"
                    )
                    enable_error_correction = st.checkbox(
                        "Enable Error Correction",
                        value=True,
                        help="Periodically check and correct errors during typing"
                    )

                col1, col2 = st.columns([1, 2])
                
                use_batch_insertion = st.checkbox("Use Batch Insertion")
                typing_speed = st.slider(
                    "Batch Typing Speed (delay in milliseconds)",
                    min_value=1,
                    max_value=100,
                    value=30,
                    help="Lower values result in faster typing"
                )
                batch_size = st.slider(
                    "Batch Size for Batch Documents",
                    min_value=5,
                    max_value=10000,
                    value=500,
                    help="Characters per batch when processing documents"
                )
                
                if use_batch_insertion:
                    if st.button("Batch Insertion", key="batch_process_btn", use_container_width=True):
                        st.session_state.processing_status = "started"
                        st.caption("Make sure the Agent is split to the browser on left or right beside your Editor for proper focus.")
                        
                        progress_bar = st.progress(1)
                        status_text = st.empty()
                        status_container = st.empty()
                        
                        keyboard = Controller()

                        def type_batch(text):
                            for char in text:
                                keyboard.type(char)
                                time.sleep(typing_speed / 1000)  # Respect the global typing delay

                        batch_typer = BatchTyper(batch_size=batch_size, batch_delay=typing_speed)
                        
                        if uploaded_file is not None:
                            file_content = extract_file_content(uploaded_file, validation_result)
                            batch_typer.load_content(content_str=file_content)
                            
                            for i in range(5, 0, -1):
                                status_container.info(f"Typing will begin in {i} seconds... Position your cursor where typing should start!")
                                time.sleep(1)
                            
                            status_container.info("Batch typing in progress...")
                            batch_typer.type_content(type_batch)
                            status_container.success("Batch typing complete!")
                        else:
                            st.error("Please upload a file first.")
                else:
                    if st.button("Start AI Typer", key="process_btn", use_container_width=True):
                        st.session_state.processing_status = "started"
                        st.caption("Make sure the Agent is split to the browser on left or right beside your Editor for proper focus.")
                        
                        progress_bar = st.progress(1)
                        status_text = st.empty()
                        status_container = st.empty()
                    
                        if uploaded_file is not None:
                            try:
                                async def process_document(doc_path, delay, error_correction):
                                    retyper = DocumentRetyper(delay=delay, model_name=selected_model)
                                    await retyper.async_init()
                                    
                                    doc_info = await retyper.display_document_info(doc_path)
                
                                    # Extract total character count for progress tracking
                                    char_count_match = re.search(r'(\d+) characters', doc_info)
                                    total_chars = int(char_count_match.group(1)) if char_count_match else 1000
                                    
                                    if doc_path.endswith('.docx'):
                                        document_text = extract_text_from_docx(doc_path)
                                    else:
                                        with open(doc_path, 'r') as f:
                                            document_text = f.read()

                                    for i in range(5, 0, -1):
                                        status_container.info(f"Typing will begin in {i} seconds... Position your cursor where typing should start!")
                                        await asyncio.sleep(1)
                                    
                                    mouse = MouseController()
                                    cursor_position = mouse.position
                                    
                                    status_container.warning("After Positioning Your Cursor. Don't Touch Your Mouse, Mouse Pad.")
                                    status_container.info("Don't move the cursor! >>>> Typing in progress...")
                                    
                                    # Setup progress tracking
                                    progress_bar.progress(0)
                                    typed_chars = 0
                                    last_update = 0

                                    async def update_typing_progress(chars_typed):
                                        nonlocal typed_chars, last_update
                                        typed_chars = chars_typed
                                        progress_percent = min(1.0, typed_chars / total_chars)
                                        
                                        if progress_percent - last_update >= 0.01:  # Update every 1% progress
                                            progress_bar.progress(progress_percent)
                                            status_text.info(f"Typing: {typed_chars}/{total_chars} characters ({int(progress_percent*100)}%)")
                                            last_update = progress_percent

                                    retyped_content = await retyper.retype_document_with_real_typing(
                                        document_text,
                                        cursor_position,
                                        error_correction,
                                        progress_callback=update_typing_progress,
                                    )
                                    progress_bar.progress(1.0)
                                    status_text.info(f"Typing: {typed_chars}/{total_chars} characters (100%)")
                                    status_container.success("✅ Document has been successfully Retyped!")
                                    return retyped_content
                                    
                                def update_progress(message, progress):
                                    status_text.info(message)
                                    progress_bar.progress(progress)
                                
                                st.write(f"File name: {uploaded_file.name}")
                                
                                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                                    tmp_file.write(uploaded_file.getvalue())
                                    temp_path = tmp_file.name
                                
                                try:
                                    result = asyncio.run(process_document(temp_path, typing_delay, enable_error_correction))
                                finally:
                                    if os.path.exists(temp_path):
                                        os.unlink(temp_path)
                            except Exception as e:
                                st.error(f"Error occurred: {str(e)}")
                        else:
                            st.error("Please upload a file first.")

                with st.expander("📄 Document Preview", expanded=False):
                    st.markdown("#### 🧾 File Content:")
                    if validation_result['type'] == 'py':
                        st.code(file_content, language=validation_result['type'])
                    else:
                        st.text_area(
                            label="Content Preview",
                            value=file_content,
                            height=400,
                            disabled=True
                        )
                
                st.caption("The Document Formats and Styles analysis,")
                
                with st.expander("🔑 Analyzer Formatter", expanded=False):
                    file_analyzed = analyze_docx(uploaded_file)
                    st.markdown("#### 🧾 File Content:")
                    if validation_result['type'] == 'py':
                        st.code(file_analyzed, language=validation_result['type'])
                    else:
                        st.text_area(
                            label="Document Contains the following Formats as Word Document Provided:",
                            value=file_analyzed,
                            height=400,
                            disabled=True
                        )
                status_container = st.empty()

                st.caption("Please If your document contains images check the box below to avoid persistent download")
                st.divider()
                st.success(f"🚨 Valid {validation_result['type'].upper()} file: {uploaded_file.name} Detected ({validation_result['size']/1024:.1f} KB)")
                st.checkbox("Images Inside🕶️", value=True, help="To avoid image download")

            except Exception as e:
                st.error(f"Error processing document: {str(e)}")
                logger.error(f"Processing error: {str(e)}")
    
    if st.session_state.processing_status == "completed" and st.session_state.result:
        st.divider()
        st.subheader("Processing Results")
        
        if not st.session_state.result.get("success", False):
            display_error_details(st.session_state.result)
        else:
            st.success("Document processed successfully!")
            st.info(st.session_state.result.get("message", "Document was processed"))
            
            if st.session_state.result.get("screenshots"):
                with st.expander("Process Screenshots", expanded=True):
                    display_screenshots(st.session_state.result["screenshots"])

with tab2:
    st.subheader("Automatic Typer")
    st.write("Here the agent will login to your vclass and submit your document")
    st.caption("For Faster Agent its for payment")
    st.subheader("🚧 Coming Soon 🚀")
    st.markdown("### 🔜 Stay Tuned! 🌟")
    st.markdown("""
    - 🛠️ We're working hard to bring this feature to life!  
    - 📅 Expected release: **TBD**  
    - 💡 Have suggestions? Let us know!  
    """)
    st.info("✨ Exciting updates are on the way. Keep an eye out! 👀")

    with st.expander("Advanced Options"):
        st.caption("Keep in mind to reset just refresh the page and Don't just set anything.")
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("Override Timer", value="", help="Leave empty to use sidebar value")
            st.text_input("Ghost Typer", value="", help="Leave empty to use sidebar value")
            
        with col2:
            st.number_input(
                "Override Typing Speed",
                value=0,
                min_value=0,
                max_value=100,
                help="Set to 0 to use sidebar value"
            )

with tab3:
    st.subheader("Contribution To Repo")
    st.caption("Leave a star ⭐")
    st.write("Please Submit a PR incase of a Push and shall be reviewed.")
    
    st.subheader("Support Us")
    st.write("If you find this tool helpful, consider supporting us!")
    st.write("Support us on [Patreon](https://patreon.com/vclassjailbreaker)")
    st.write("Support us on [Binance](https://paypal.me/vclassjailbreaker)")
    st.write("Support us on [PayPal](https://paypal.me/vclassjailbreaker)")

with tab4:
    st.subheader("Settings Guide")
    st.write("The Automation process for the Agent to Login to your vclass and also to submit your document")
    st.caption("Coming Soon: But first support to try for Free and Remember we are not responsible for anything.")
    st.write("""
    - **Typing Speed**: Reduce this for more accurate typing (recommended: 20-25 chars/sec)
    - **Chunk Size**: For larger documents, smaller chunks are processed more reliably
    - **Headless Mode**: Run the browser invisibly in the background
    - **Screenshots**: Capture images to verify the document was typed correctly
    """)
    
    st.subheader("Troubleshooting")
    st.write("""
    If the automation is not working correctly:
    1. Try a slower typing speed (15-20 chars/sec)
    2. Use smaller chunk sizes (2000-3000 chars)
    3. Make sure your login credentials are correct
    4. Check that the document format is supported (.odt, .docx, .py, .md)
    5. For complex documents, consider simplifying the formatting
    """)

st.divider()
st.caption("We value your privacy. This application does not store any data. | Made with ❤️ at Victoria Uni")