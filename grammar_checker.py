from typing import Any, Dict, List
import language_tool_python


try:
    language_tool = language_tool_python.LanguageTool('en-US')
except:
    print("Warning: LanguageTool could not be initialized. Grammar checking will be disabled.")
    language_tool = None


class GrammarChecker:
    """Class to check grammar and provide corrections"""
    
    def __init__(self):
        self.language_tool = language_tool
    
    def check_grammar(self, text: str) -> List[Dict]:
        """Check grammar and return corrections"""
        if not self.language_tool:
            return []
        
        # Get matches from language tool
        matches = self.language_tool.check(text)
        
        corrections = []
        for match in matches:
            if match.replacements:
                corrections.append({
                    "type": "grammar",
                    "message": match.message,
                    "offset": match.offset,
                    "length": match.errorLength,
                    "replacements": match.replacements,
                    "rule_id": match.ruleId
                })
        
        return corrections
    
    def apply_correction(self, text: str, correction: Dict) -> str:
        """Apply a single correction to the text"""
        if correction["type"] == "grammar" and correction["replacements"]:
            # Replace the text at the given offset with the first suggestion
            offset = correction["offset"]
            length = correction["length"]
            replacement = correction["replacements"][0]
            
            return text[:offset] + replacement + text[offset + length:]
        
        return text

#=====================================================================================
class DocumentVerifier:
    """Class to verify document content and detect errors"""
    def __init__(self):
        pass
    
    def compare_content(self, original: str, typed: str) -> Dict[str, Any]:
        """Compare original content with typed content to detect errors"""
        # Split into lines for comparison
        original_lines = original.split('\n')
        typed_lines = typed.split('\n')
        
        errors = []
        
        # Check length difference first
        if len(original_lines) != len(typed_lines):
            errors.append({
                "type": "line_count_mismatch",
                "message": f"Line count mismatch: {len(original_lines)} vs {len(typed_lines)}"
            })
        
        # Compare line by line
        for i, (orig, typed) in enumerate(zip(original_lines, typed_lines[:len(original_lines)])):
            if orig != typed:
                # Find the position of the first difference
                pos = next((j for j in range(min(len(orig), len(typed))) if orig[j] != typed[j]), min(len(orig), len(typed)))
                errors.append({
                    "type": "content_mismatch",
                    "line": i + 1,
                    "position": pos + 1,
                    "original": orig,
                    "typed": typed
                })
        
        return {
            "match": len(errors) == 0,
            "errors": errors
        }
