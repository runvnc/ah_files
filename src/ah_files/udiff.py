import difflib
from pathlib import Path
import os

def normalize_line_endings(text):
    """Convert all line endings to \n"""
    return text.replace('\r\n', '\n').replace('\r', '\n')

def parse_hunk_header(header):
    """Parse @@ -start,length +start,length @@ header"""
    parts = header.split()
    if not parts[0].startswith("@@"):
        return None
    
    try:
        old_range = parts[1][1:].split(',')  # Remove the - and split
        new_range = parts[2][1:].split(',')  # Remove the + and split
        
        old_start = int(old_range[0])
        old_length = int(old_range[1]) if len(old_range) > 1 else 1
        new_start = int(new_range[0])
        new_length = int(new_range[1]) if len(new_range) > 1 else 1
        
        return (old_start, old_length, new_start, new_length)
    except:
        return None

def apply_hunk(content, hunk):
    """Apply a single hunk to the content"""
    if not hunk:
        return content
        
    print("DEBUG: Starting apply_hunk")
    print("DEBUG: Received hunk lines:")
    for line in hunk:
        print(f"DEBUG: HUNK LINE: {repr(line)}")
        
    # Normalize line endings in content
    content = normalize_line_endings(content)
    
    # Split content into lines for processing
    lines = content.splitlines(True)  # Keep line endings
    
    # Find the hunk header
    header_line = None
    for i, line in enumerate(hunk):
        if line.startswith("@@"):
            header_line = i
            break
            
    if header_line is None:
        print("DEBUG: No header line found")
        return content
        
    # Parse the hunk header
    header_info = parse_hunk_header(hunk[header_line])
    if not header_info:
        print("DEBUG: Could not parse header")
        return content
        
    old_start, old_length, new_start, new_length = header_info
    print(f"DEBUG: Header info: old_start={old_start}, old_length={old_length}, new_start={new_start}, new_length={new_length}")
    
    # Extract the before content from the hunk
    before_lines = []
    for line in hunk[header_line + 1:]:
        if line.startswith(" ") or line.startswith("-"):
            # Normalize line endings in the hunk lines
            normalized = normalize_line_endings(line[1:])
            before_lines.append(normalized)
            print(f"DEBUG: Added before line: {repr(normalized)}")
            
    # Find the location in the original content
    before_text = "".join(before_lines)
    content_text = "".join(lines)
    
    print("DEBUG: Before text:", repr(before_text))
    print("DEBUG: Content text:", repr(content_text))
    
    # Find where this chunk should go
    chunk_pos = content_text.find(before_text)
    print("DEBUG: Chunk position:", chunk_pos)
    
    if chunk_pos == -1:
        print("DEBUG: Could not find chunk in content")
        return content  # Can't find the chunk, return unchanged
        
    # Now extract the after content
    after_lines = []
    for line in hunk[header_line + 1:]:
        if line.startswith(" ") or line.startswith("+"):
            # Normalize line endings in the hunk lines
            normalized = normalize_line_endings(line[1:])
            after_lines.append(normalized)
            print(f"DEBUG: Added after line: {repr(normalized)}")
            
    after_text = "".join(after_lines)
    print("DEBUG: After text:", repr(after_text))
    
    # Create the new content by replacing just this chunk
    new_content = content_text[:chunk_pos] + after_text + content_text[chunk_pos + len(before_text):]
    return new_content

class UnifiedDiffCoder:
    def __init__(self, io):
        self.io = io

    def get_edits(self, diff_content):
        """Parse the unified diff into a list of (path, hunk) tuples"""
        print("\nDEBUG: Starting get_edits")
        print("DEBUG: Received diff content:", repr(diff_content))
        
        edits = []
        current_path = None
        current_hunk = []
        
        # Normalize line endings in the diff content
        diff_content = normalize_line_endings(diff_content)
        
        lines = diff_content.splitlines(keepends=True)
        for line in lines:
            print("DEBUG: Processing line:", repr(line))
            if line.startswith("--- "):
                if current_hunk:
                    print("DEBUG: Adding hunk for path", current_path)
                    edits.append((current_path, current_hunk))
                    current_hunk = []
                current_path = line[4:].strip()
                print("DEBUG: Found source file:", current_path)
            elif line.startswith("+++ "):
                current_path = line[4:].strip()
                print("DEBUG: Found target file:", current_path)
            elif line.startswith("@@"):
                if current_hunk:
                    print("DEBUG: Adding hunk for path", current_path)
                    edits.append((current_path, current_hunk))
                current_hunk = [line]
                print("DEBUG: Started new hunk with header:", repr(line))
            elif line.startswith(("-", "+", " ")) and current_hunk:
                current_hunk.append(line)
                print("DEBUG: Added line to hunk:", repr(line))
                
        if current_hunk:
            print("DEBUG: Adding final hunk for path", current_path)
            edits.append((current_path, current_hunk))
            
        print("DEBUG: Final edits list:")
        for path, hunk in edits:
            print(f"DEBUG: Path: {repr(path)}")
            print("DEBUG: Hunk lines:")
            for line in hunk:
                print(f"DEBUG: {repr(line)}")
        return edits

    def apply_edits(self, edits):
        """Apply all edits to their respective files"""
        print("\nDEBUG: Starting apply_edits")
        print("DEBUG: Received edits:")
        for path, hunk in edits:
            print(f"DEBUG: Edit for path: {repr(path)}")
            print("DEBUG: Hunk lines:")
            for line in hunk:
                print(f"DEBUG: {repr(line)}")
        
        cnt = 0
        for path, hunk in edits:
            if not path or path == "/dev/null":
                continue
                
            # Handle relative paths
            if not os.path.isabs(path):
                path = os.path.basename(path)
            
            full_path = self.io.abs_path(path)
            print(f"DEBUG: Processing file: {full_path}")
            content = self.io.read_text(full_path)
            print("DEBUG: File content:", repr(content))
            
            new_content = apply_hunk(content, hunk)
            if new_content != content:
                cnt += 1
                self.io.write_text(full_path, new_content)
                print("DEBUG: File was modified")
            else:
                print("DEBUG: No changes made to file")
                
        return cnt

class MockIO:
    def __init__(self, root):
        self.root = Path(root)
        self.files = {}
        
    def abs_path(self, path):
        return str(self.root / path)
    
    def read_text(self, path):
        path = self.abs_path(path)
        return self.files.get(path, "")
    
    def write_text(self, path, content):
        path = self.abs_path(path)
        self.files[path] = content

class FileIO:
    def __init__(self, root):
        self.root = Path(root)

    def abs_path(self, path):
        path = Path(path)
        if not path.is_absolute():
            path = self.root / path
        return path
    
    def read_text(self, path):
        path = self.abs_path(path)
        with open(path) as f:
            return f.read()
            
    def write_text(self, path, content):
        path = self.abs_path(path)
        with open(path, "w") as f:
            f.write(content)
