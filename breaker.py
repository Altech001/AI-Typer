import time
import asyncio
import re
from grammar_checker import DocumentVerifier, GrammarChecker
import random
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
import keyboard


class RealKeyboardTyper:
    """Class to perform real keyboard typing using pynput with error correction"""
    def __init__(self, delay=0.005, verify_interval=1000):  # Slightly slower for reliability
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        self.grammar_checker = GrammarChecker()
        self.delay = delay
        self.verify_interval = verify_interval  # Check every X characters
        self.document_verifier = DocumentVerifier()

    def toggle_bold(self):
        """Toggle bold formatting using Ctrl+B shortcut"""
        with self.keyboard.pressed(Key.ctrl):
            self.keyboard.press('b')
            self.keyboard.release('b')
        time.sleep(0.005)

    def toggle_underline(self):
        """Toggle underline formatting using Ctrl+U shortcut"""
        with self.keyboard.pressed(Key.ctrl):
            self.keyboard.press('u')
            self.keyboard.release('u')
        time.sleep(0.1)

    def toggle_italic(self):
        """Toggle italic formatting using Ctrl+I shortcut"""
        with self.keyboard.pressed(Key.ctrl):
            self.keyboard.press('i')
            self.keyboard.release('i')
        time.sleep(0.1)

    def click_and_focus(self, position=None):
        """Click at specified coordinates to focus or use current position"""
        if position:
            # Save current position
            old_pos = self.mouse.position
            # Move to target position
            self.mouse.position = position
            time.sleep(0.005)
            # Click to focus
            self.mouse.click(Button.left)
            time.sleep(0.005)
            # Return to original position to avoid interference
            self.mouse.position = old_pos
        else:
            # Just click at current position
            self.mouse.click(Button.left)
            time.sleep(0.005)
    
    def select_all_and_delete(self):
        """Select all text and delete it to start fresh"""
        with self.keyboard.pressed(Key.ctrl):
            self.keyboard.press('a')
            self.keyboard.release('a')
        time.sleep(0.1)
        self.keyboard.press(Key.delete)
        self.keyboard.release(Key.delete)
        time.sleep(0.1)

    async def type_with_formatting(self, text, focus_position=None):
        """Type text with formatting support for bold, italic, and underline"""
        # Initial focus
        self.click_and_focus(focus_position)
        
        # Process text with formatting markers
        # For example, you could use markers like **bold**, _italic_, __underline__
        
        i = 0
        while i < len(text):
            # Check for bold markers
            if text[i:i+2] == "**" and "**" in text[i+2:]:
                # Skip the opening marker
                i += 2
                # Find the closing marker
                end_bold = text.find("**", i)
                if end_bold != -1:
                    # Get the text to be bolded
                    bold_text = text[i:end_bold]
                    # Toggle bold on
                    self.toggle_bold()
                    # Type the text
                    for char in bold_text:
                        if not self.handle_special_char(char):
                            self.keyboard.press(char)
                            self.keyboard.release(char)
                        await asyncio.sleep(self.delay)
                    # Toggle bold off
                    self.toggle_bold()
                    # Skip to after the closing marker
                    i = end_bold + 2
                    continue
            
            # Check for underline markers (similar logic)
            if text[i:i+2] == "__" and "__" in text[i+2:]:
                # Skip the opening marker
                i += 2
                # Find the closing marker
                end_underline = text.find("__", i)
                if end_underline != -1:
                    # Get the text to be underlined
                    underline_text = text[i:end_underline]
                    # Toggle underline on
                    self.toggle_underline()
                    # Type the text
                    for char in underline_text:
                        if not self.handle_special_char(char):
                            self.keyboard.press(char)
                            self.keyboard.release(char)
                        await asyncio.sleep(self.delay)
                    # Toggle underline off
                    self.toggle_underline()
                    # Skip to after the closing marker
                    i = end_underline + 2
                    continue
            
            # Type regular character
            if not self.handle_special_char(text[i]):
                self.keyboard.press(text[i])
                self.keyboard.release(text[i])
            
            # Move to next character
            i += 1
            await asyncio.sleep(self.delay)
    
    def handle_special_char(self, char):
        """Handle typing of special characters"""
        if char == '\n':
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)
            return True
        elif char == '\t':
            self.keyboard.press(Key.tab)
            self.keyboard.release(Key.tab)
            return True
        elif char == ' ':
            self.keyboard.press(Key.space)
            self.keyboard.release(Key.space)
            return True
        return False
    
    def handle_text_selection(self, count=1, direction="forward"):
        """Handle text selection for correction"""
        key = Key.right if direction == "forward" else Key.left
        with self.keyboard.pressed(Key.shift):
            for _ in range(count):
                self.keyboard.press(key)
                self.keyboard.release(key)
                time.sleep(0.01)
    
    def preserve_formatting_boundaries(self, text):
        """Ensure proper formatting boundaries are preserved"""
        # Make sure paragraph breaks are preserved
        preserved = text
        # Replace single newlines between paragraphs with double newlines if not already
        preserved = re.sub(r'([^\n])\n([^\n])', r'\1\n\n\2', preserved)
        return preserved
    
    async def apply_corrections(self, expected, actual):
        """Apply corrections to make actual text match expected text"""
        if expected == actual:
            return
        
        # Calculate differences
        min_len = min(len(expected), len(actual))
        
        # Find the first position where they differ
        diff_pos = 0
        for i in range(min_len):
            if expected[i] != actual[i]:
                diff_pos = i
                break
        else:
            # If no difference found in common length, the difference is in length
            diff_pos = min_len
        
        # Calculate how many characters to delete and what to type
        chars_to_delete = len(actual) - diff_pos
        chars_to_type = expected[diff_pos:]
        
        if chars_to_delete > 0:
            # Select and delete the incorrect characters
            for _ in range(chars_to_delete):
                self.keyboard.press(Key.backspace)
                self.keyboard.release(Key.backspace)
                await asyncio.sleep(0.01)
        
        # Type the correct characters
        for char in chars_to_type:
            if not self.handle_special_char(char):
                self.keyboard.press(char)
                self.keyboard.release(char)
            await asyncio.sleep(self.delay)
            
    async def type_with_verification(self, text, focus_position=None, error_correction=True,progress_callback=None):
        """Type text with periodic verification and error correction"""
        # Initial focus
        self.click_and_focus(focus_position)
        
        # Ensure proper formatting boundaries
        text = self.preserve_formatting_boundaries(text)
        
        # Variables for cursor tracking
        cursor_line = 0
        cursor_pos = 0
        typed_content = ""
        
        # Type character by character with verification
        char_count = 0
        segments = text.split('\n')
        
        for i, segment in enumerate(segments):
            # Type each character in the segment
            for j, char in enumerate(segment):
                # Update cursor position tracking
                cursor_pos = j
                
                # Regular typing with error handling
                try:
                    # Type the character
                    self.keyboard.press(char)
                    self.keyboard.release(char)
                    typed_content += char
                except Exception as e:
                    print(f"Error typing character '{char}': {str(e)}")
                    # Try alternative method for problematic characters
                    try:
                        keyboard.write(char)
                        typed_content += char
                    except:
                        print(f"Failed to type character '{char}'")
                
                # Update progress
                char_count += 1
                if progress_callback and char_count % 5 == 0:  # Update every 5 characters to avoid too frequent updates
                    await progress_callback(char_count)
                
                # Dynamic delay between keystrokes for realistic typing
                typing_delay = self.delay + (0.01 * (0.5 - random.random()))
                await asyncio.sleep(typing_delay)
                
                # Verify every X characters if enabled
                char_count += 1
                if error_correction and char_count % self.verify_interval == 0:
                    await self.verify_and_correct(text[:len(typed_content)], typed_content, cursor_line, cursor_pos)

                if error_correction and char_count % self.verify_interval == 0:
                    expected_so_far = text[:len(typed_content)]
                    await self.apply_corrections(expected_so_far, typed_content)
                    
                    # Check grammar in the last sentence
                    last_sentence = re.split(r'[.!?]', typed_content)[-1]
                    if len(last_sentence) > 10:  # Only check substantial sentences
                        corrections = self.grammar_checker.check_grammar(last_sentence)
                        if corrections:
                            print(f"Grammar correction suggested: {corrections[0]['message']}")
                            
                    
            # Add newline if not the last segment
            if i < len(segments) - 1:
                self.keyboard.press(Key.enter)
                self.keyboard.release(Key.enter)
                typed_content += '\n'
                cursor_line += 1
                cursor_pos = 0
                await asyncio.sleep(self.delay)
        
        # Final verification
        if error_correction:
            await self.verify_and_correct(text, typed_content, cursor_line, cursor_pos)
        
        if progress_callback:
            await progress_callback(len(typed_content))
        
        return typed_content
    
    def preserve_formatting_boundaries(self, text):
        """Ensure proper formatting boundaries are preserved"""
        # Make sure paragraph breaks are preserved
        preserved = text
        # Replace single newlines between paragraphs with double newlines if not already
        preserved = re.sub(r'([^\n])\n([^\n])', r'\1\n\n\2', preserved)
        return preserved
    
    async def verify_and_correct(self, expected, actual, current_line, current_pos):
        """Verify typed content and attempt to correct errors"""
        # Save original cursor position
        original_line = current_line
        original_pos = current_pos
        
        # Skip verification if strings match exactly
        if expected == actual:
            return
        
        # Simple check for line count discrepancy
        expected_lines = expected.count('\n') + 1
        actual_lines = actual.count('\n') + 1
        
        if expected_lines != actual_lines:
            print(f"Warning: Line count mismatch - expected {expected_lines}, got {actual_lines}")
            
            # Try to correct by moving to the end and adding needed newlines
            for _ in range(abs(expected_lines - actual_lines)):
                self.keyboard.press(Key.enter)
                self.keyboard.release(Key.enter)
                await asyncio.sleep(0.05)
        
        # Look for character mismatches and try to correct them
        comparison = self.document_verifier.compare_content(expected, actual)
        
        if not comparison["match"] and len(comparison["errors"]) > 0:
            print(f"Detected {len(comparison['errors'])} errors, attempting to correct...")
            
            # We'll implement a simple correction for the first error
            if len(comparison["errors"]) > 0:
                err = comparison["errors"][0]
                if err["type"] == "content_mismatch":
                    # Try to navigate to the error position
                    # This is a simplified approach - more sophisticated navigation would be needed
                    # for real-world applications
                    
                    # First press Escape to ensure we're not in any special mode
                    self.keyboard.press(Key.esc)
                    self.keyboard.release(Key.esc)
                    await asyncio.sleep(0.1)
                    
                    # Try to correct by retyping the problematic part
                    print(f"Attempting recovery...")
                    self.click_and_focus()
                    await asyncio.sleep(0.1)
                    
                    # Select all and delete as a recovery method
                    self.select_all_and_delete()
                    
                    # Retype from the beginning of the problematic section
                    # For simplicity, we'll just retype a portion of the text
                    recovery_text = expected[:min(len(expected), 200)]  # Just first 200 chars for demo
                    for recovery_char in recovery_text:
                        if not self.handle_special_char(recovery_char):
                            self.keyboard.press(recovery_char)
                            self.keyboard.release(recovery_char)
                        await asyncio.sleep(self.delay)

    async def type_text(self, text, focus_position=None):
        """Type the text using real keyboard inputs with proper focus management"""
        # Initial focus
        if focus_position:
            self.click_and_focus(focus_position)
        else:
            self.click_and_focus()
        
        # Set up a mouse position check interval to maintain focus
        last_check = time.time()
        check_interval = 1.0  # Check focus more frequently (every 1 second)
        
        # Remember initial position to check if mouse moved
        initial_pos = self.mouse.position
        
        # Keep track of what we've typed for verification
        typed_text = ""
        
        # Split text by paragraphs to handle formatting better
        paragraphs = re.split(r'\n\s*\n', text)
        
        for i, paragraph in enumerate(paragraphs):
            # Check if we need to refocus
            current_time = time.time()
            if current_time - last_check > check_interval:
                # Check if mouse has moved significantly
                current_pos = self.mouse.position
                distance = ((current_pos[0] - initial_pos[0])**2 + 
                           (current_pos[1] - initial_pos[1])**2)**0.5
                
                if distance > 5:  # Mouse moved more than 5 pixels
                    # Refocus by clicking
                    print("Mouse moved - refocusing...")
                    self.click_and_focus(initial_pos)
                    initial_pos = self.mouse.position  # Update initial position
                
                last_check = current_time
            
            # Type each character in the paragraph
            for char in paragraph:
                # Handle special characters
                if not self.handle_special_char(char):
                    # Type the character
                    self.keyboard.press(char)
                    self.keyboard.release(char)
                
                typed_text += char
                
                # Dynamic delay between keystrokes for realistic typing
                typing_delay = self.delay + (0.01 * (0.5 - random.random()))
                await asyncio.sleep(typing_delay)
            
            # Add paragraph breaks between paragraphs, except after the last one
            if i < len(paragraphs) - 1:
                # Add two newlines for paragraph breaks
                self.keyboard.press(Key.enter)
                self.keyboard.release(Key.enter)
                await asyncio.sleep(self.delay)
                self.keyboard.press(Key.enter)
                self.keyboard.release(Key.enter)
                await asyncio.sleep(self.delay)
                typed_text += "\n\n"
        
        return typed_text
