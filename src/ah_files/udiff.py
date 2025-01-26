import difflib
from pathlib import Path

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
        
    # Split content into lines for processing
    lines = content.splitlines(True)  # Keep line endings
    
    # Find the hunk header
    header_line = None
    for i, line in enumerate(hunk):
        if line.startswith("@@"):
            header_line = i
            break
            
    if header_line is None:
        return content
        
    # Parse the hunk header
    header_info = parse_hunk_header(hunk[header_line])
    if not header_info:
        return content
        
    old_start, old_length, new_start, new_length = header_info
    
    # Extract the before content from the hunk
    before_lines = []
    for line in hunk[header_line + 1:]:
        if line.startswith(" ") or line.startswith("-"):
            before_lines.append(line[1:])
            
    # Find the location in the original content
    before_text = "".join(before_lines)
    content_text = "".join(lines)
    
    # Debug output
    print("\nDEBUG - Before text (hex):", before_text.encode('utf-8').hex())
    print("DEBUG - Content excerpt (hex):", content_text[0:100].encode('utf-8').hex())
    print("\nDEBUG - Before text (repr):", repr(before_text))
    print("DEBUG - Content excerpt (repr):", repr(content_text[0:100]))
    
    # Find where this chunk should go
    chunk_pos = content_text.find(before_text)
    print("\nDEBUG - Chunk position:", chunk_pos)
    
    if chunk_pos == -1:
        return content  # Can't find the chunk, return unchanged
        
    # Now extract the after content
    after_lines = []
    for line in hunk[header_line + 1:]:
        if line.startswith(" ") or line.startswith("+"):
            after_lines.append(line[1:])
            
    after_text = "".join(after_lines)
    
    # Create the new content by replacing just this chunk
    new_content = content_text[:chunk_pos] + after_text + content_text[chunk_pos + len(before_text):]
    return new_content

class UnifiedDiffCoder:
    def __init__(self, io):
        self.io = io

    def get_edits(self, diff_content):
        """Parse the unified diff into a list of (path, hunk) tuples"""
        edits = []
        current_path = None
        current_hunk = []
        
        lines = diff_content.splitlines(keepends=True)
        for line in lines:
            if line.startswith("--- "):
                if current_hunk:
                    edits.append((current_path, current_hunk))
                    current_hunk = []
                current_path = line[4:].strip()
            elif line.startswith("+++ "):
                current_path = line[4:].strip()
            elif line.startswith("@@"):
                if current_hunk:
                    edits.append((current_path, current_hunk))
                current_hunk = [line]
            elif line.startswith(("-", "+", " ")) and current_hunk:
                current_hunk.append(line)
                
        if current_hunk:
            edits.append((current_path, current_hunk))
            
        return edits

    def apply_edits(self, edits):
        """Apply all edits to their respective files"""
        cnt = 0
        for path, hunk in edits:
            if not path or path == "/dev/null":
                continue
                
            full_path = self.io.abs_path(path)
            content = self.io.read_text(full_path)
            
            new_content = apply_hunk(content, hunk)
            if new_content != content:
                cnt += 1
                self.io.write_text(full_path, new_content)
                
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
