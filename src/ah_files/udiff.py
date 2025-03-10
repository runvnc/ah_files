import difflib
from itertools import groupby
from pathlib import Path
from .search_replace import (
    SearchTextNotUnique,
    all_preprocs,
    diff_lines,
    flexible_search_and_replace,
    search_and_replace,
)

def normalize_line_endings(text):
    """Convert all line endings to \n"""
    return text.replace('\r\n', '\n').replace('\r', '\n')

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

def flexi_just_search_and_replace(texts):
    strategies = [
        (search_and_replace, all_preprocs),
    ]
    return flexible_search_and_replace(texts, strategies)

def apply_hunk(content, hunk):
    before_text, after_text = hunk_to_before_after(hunk)

    res = directly_apply_hunk(content, hunk)
    if res:
        return res

    hunk = make_new_lines_explicit(content, hunk)

    # just consider space vs not-space
    ops = "".join([line[0] for line in hunk])
    ops = ops.replace("-", "x")
    ops = ops.replace("+", "x")
    ops = ops.replace("\n", " ")

    cur_op = " "
    section = []
    sections = []

    for i in range(len(ops)):
        op = ops[i]
        if op != cur_op:
            sections.append(section)
            section = []
            cur_op = op
        section.append(hunk[i])

    sections.append(section)
    if cur_op != " ":
        sections.append([])

    all_done = True
    for i in range(2, len(sections), 2):
        preceding_context = sections[i - 2]
        changes = sections[i - 1]
        following_context = sections[i]

        res = apply_partial_hunk(content, preceding_context, changes, following_context)
        if res:
            content = res
        else:
            all_done = False
            break

    if all_done:
        return content

def make_new_lines_explicit(content, hunk):
    before, after = hunk_to_before_after(hunk)

    diff = diff_lines(before, content)

    back_diff = []
    for line in diff:
        if line[0] == "+":
            continue
        back_diff.append(line)

    new_before = directly_apply_hunk(before, back_diff)
    if not new_before:
        return hunk

    if len(new_before.strip()) < 10:
        return hunk

    before = before.splitlines(keepends=True)
    new_before = new_before.splitlines(keepends=True)
    after = after.splitlines(keepends=True)

    if len(new_before) < len(before) * 0.66:
        return hunk

    new_hunk = difflib.unified_diff(new_before, after, n=max(len(new_before), len(after)))
    new_hunk = list(new_hunk)[3:]

    return new_hunk

def directly_apply_hunk(content, hunk):
    before, after = hunk_to_before_after(hunk)

    if not before:
        return

    before_lines, _ = hunk_to_before_after(hunk, lines=True)
    before_lines = "".join([line.strip() for line in before_lines])

    # Refuse to do a repeated search and replace on a tiny bit of non-whitespace context
    if len(before_lines) < 10 and content.count(before) > 1:
        return

    try:
        new_content = flexi_just_search_and_replace([before, after, content])
    except SearchTextNotUnique:
        new_content = None

    return new_content

def apply_partial_hunk(content, preceding_context, changes, following_context):
    len_prec = len(preceding_context)
    len_foll = len(following_context)

    use_all = len_prec + len_foll

    # if there is a - in the hunk, we can go all the way to `use=0`
    for drop in range(use_all + 1):
        use = use_all - drop

        for use_prec in range(len_prec, -1, -1):
            if use_prec > use:
                continue

            use_foll = use - use_prec
            if use_foll > len_foll:
                continue

            if use_prec:
                this_prec = preceding_context[-use_prec:]
            else:
                this_prec = []

            this_foll = following_context[:use_foll]

            res = directly_apply_hunk(content, this_prec + changes + this_foll)
            if res:
                return res

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
                
            # FileIO.abs_path already handles both absolute and relative paths correctly
            # by joining relative paths with the root directory
            
            full_path = self.io.abs_path(path)
            content = self.io.read_text(full_path)
            
            new_content = apply_hunk(content, hunk)
            if new_content and new_content != content:
                cnt += 1
                self.io.write_text(full_path, new_content)
                
        return cnt

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
