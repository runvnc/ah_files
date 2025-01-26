import difflib
from pathlib import Path

def hunk_to_before_after(hunk, lines=False):
    before = []
    after = []
    op = " "
    for line in hunk:
        if len(line) < 2:
            op = " "
            line = line
        else:
            op = line[0]
            line = line[1:]

        if op == " ":
            before.append(line)
            after.append(line)
        elif op == "-":
            before.append(line)
        elif op == "+":
            after.append(line)

    if lines:
        return before, after

    before = "".join(before)
    after = "".join(after)

    return before, after

def directly_apply_hunk(content, hunk):
    before, after = hunk_to_before_after(hunk)

    if not before:
        return content

    # Find the location of the before text
    pos = content.find(before)
    if pos == -1:
        return None

    # Check for uniqueness
    if content.find(before, pos + 1) != -1:
        return None

    # Replace the content
    new_content = content[:pos] + after + content[pos + len(before):]
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
                
            # Handle relative paths
            if not Path(path).is_absolute():
                path = Path(path).name
            
            full_path = self.io.abs_path(path)
            content = self.io.read_text(full_path)
            
            new_content = directly_apply_hunk(content, hunk)
            if new_content and new_content != content:
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