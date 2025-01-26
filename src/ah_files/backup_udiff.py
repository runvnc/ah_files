import difflib
from pathlib import Path

class UnifiedDiffCoder:
    def __init__(self, io):
        self.io = io

    def get_edits(self, diff_content):
        edits = []
        current_path = None
        
        lines = diff_content.splitlines(keepends=True)
        for line in lines:
            if line.startswith("--- "):
                current_path = line[4:].strip()
            elif line.startswith("+++ "):
                current_path = line[4:].strip()
            elif line.startswith("@@"):
                hunk = []
                edits.append((current_path, hunk))
            elif line.startswith(("-", "+", " ")):
                if edits:
                    edits[-1][1].append(line)
        
        return edits

    def apply_edits(self, edits):
        cnt = 0
        for path, hunk in edits:
            full_path = self.io.abs_path(path)
            content = self.io.read_text(full_path)
            
            before, after = hunk_to_before_after(hunk)
            new_content = apply_hunk(content, hunk)
            
            if new_content:
                cnt += 1
                self.io.write_text(full_path, new_content)
        return cnt

def hunk_to_before_after(hunk):
    before = []
    after = []
    for line in hunk:
        if line.startswith(" "):
            before.append(line[1:])
            after.append(line[1:])
        elif line.startswith("-"):
            before.append(line[1:])
        elif line.startswith("+"):
            after.append(line[1:])
    return "".join(before), "".join(after)

def apply_hunk(content, hunk):
    before, after = hunk_to_before_after(hunk)
    
    differ = difflib.Differ()
    diff = list(differ.compare(content.splitlines(keepends=True), after.splitlines(keepends=True)))
    output = []
    for line in diff:
        if line.startswith("  ") or line.startswith("+ "):
            output.append(line[2:])
    
    return "".join(output)

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

# uses actual read() and write to files
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


if __name__ == "__main__":
    # Example usage
    io = FileIO("/tmp/udiff-example")
    coder = UnifiedDiffCoder(io)
    
    # Create initial file
    io.write_text("example.py", '''def subtract(a, b):
    return a - b
''')
    
    # Unified diff to apply
    diff = '''--- example.py
+++ example.py
@@ -1,2 +1,9 @@
 def subtract(a, b):
+    """Subtracts b from a"""
-    return a - b
+    return (a - b)     
+
+def multiply(a, b):
+    """Multiplies two numbers"""
+    return a * b
'''
    
    edits = coder.get_edits(diff)
    num_edits = coder.apply_edits(edits)
    print(f"Applied {num_edits} edits")
    print("Updated content:")
    print(io.read_text("example.py"))

