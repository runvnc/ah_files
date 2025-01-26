from .make_file_backup import backup_file, restore_file
from lib.providers.commands import command
import os
import glob
import json
from datetime import datetime
import shutil
from .numbered import numbered_file_to_string, replace_lines_impl
from .udiff import UnifiedDiffCoder, FileIO

def check_path(fname):
    dirname = os.path.dirname(fname)
    if not dirname or dirname == '':
        raise Exception("Absolute path to file must be specified")
    return dirname

@command()
async def append(fname, text, context=None):
    """Append text to a file. If the file doesn't exist, it will be created.

       Don't try to output too much text at once.
       Instead, append a portion at a time, waiting for the system to acknowledge 
       each command.

    fname must be the absolute path to the file

    Example:

    { "append": { "fname": "/path/to/file1.txt",
                 "text": START_RAW
    This is the text to be appended to the file.
    Line 2.
    END_RAW
    } }
    """
    dirname = os.path.dirname(fname)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    
    with open(fname, 'a') as f:
        f.write(text)
    
    print(f'Appended text to {fname}')
    return True

@command()
async def write(fname, text, context=None):
    """This is an alias for the overwrite() command."""
    return await overwrite(fname, text, context)

@command()
async def overwrite(fname, text, context=None):
    """Write text to a file. Will overwrite the file if it exists.
    Make sure you know the full path first.
    Note: All text must be provided to be written to the file. Do NOT include placeholders,
    as the text will be written exactly as provided and will ovewrite any existing content.

    For large amounts of text, use append() with multiple commands.

    fname MUST be the absolute path to the file.

    Important: use the RAW string block encoding for the text parameter,
            especially if you have special characters or newlines.

    Example:

    { "overwrite": { "fname": "/path/to/file1.txt",
                 "text": START_RAW
    This is the text to write to the file.
    Line 2.
    END_RAW
               }
    }

    Obviously you should not start a new command list if you are already in one.

    """
    dirname = check_path(fname)

    if not os.path.exists(dirname):
        os.makedirs(dirname)

    old_line_count = 0
    if os.path.isfile(fname):
        # read the file in and count the number of lines
        with open(fname, 'r') as f:
            old_text = f.read()
            old_line_count = old_text.count('\n') + 1
            print(f"Read {fname} with {old_line_count} lines")
        backup_file(fname)
    
    with open(fname, 'w') as f:
        f.write(text)
    
    line_count = text.count('\n') + 1
    print(f"Wrote text to {fname} line count: {line_count}")
    if old_line_count > 0:
        return f"[SYSTEM command result, NOT user reply: Wrote {fname}. File now contains {line_count} lines, previously {old_line_count} lines.]"
    else:
        return f"[SYSTEM command result, NOT user reply: Wrote {fname}. File now contains a total of {line_count} lines.]"

@command()
async def read(fname, context=None):
    """Read text from a file.
    You must specify the full path to the file.
    Example:
    { "read": { "fname": "/path/to/file1.txt" } }
    """
    dirname = check_path(fname)

    with open(fname, 'r') as f:
        text = f.read()
        print(f'Read text from {fname}: {text}')
        return text

@command()
async def replace_inclusive(fname, starts_with, ends_with, text, context=None):
    """Replace text between two unique strings in a file, including start and end strings.

    Parameters:

    fname - The absolute path to the file to replace text in.
    starts_with - The JSON-encoded/safe start string. Must be unique in the file.
    ends_with - The JSON-encoded/safe end string. Must be unique in the file and appear after starts_with.
    text - The JSON-encoded/safe text to replace existing content with, including start and end strings.

    Important:
    - Strings must be properly escaped as this is a JSON command (e.g., escape newlines, double quotes).
    - The 'starts_with' and 'ends_with' strings MUST be unique in the file to avoid ambiguity.
    - 'starts_with' must appear before 'ends_with' in the file.
    - The new 'text' must include both 'starts_with' and 'ends_with' to maintain file structure.

    Returns:
    Boolean indicating success.

    Raises:
    Exception: If starts_with or ends_with is not found, not unique, or in wrong order.

    Example:

    { "replace_inclusive": { 
        "fname": "/path/to/example.py", 
        "starts_with": "def unique_function():\n", 
        "ends_with": "\n    return 'unique string'", 
        "text": "def unique_function():\n    print('This is a unique function')\n    return 'unique string'"
    } }
    """

    # Read file content
    with open(fname, 'r') as f:
        content = f.read()

    # Find the section to replace
    start_index = content.find(starts_with)
    if start_index == -1:
        raise Exception(f"Could not find starts_with string: {starts_with}")

    end_index = content.find(ends_with, start_index)
    if end_index == -1:
        raise Exception(f"Could not find ends_with string: {ends_with}")

    # Check for multiple occurrences
    if content.count(starts_with) > 1 or content.count(ends_with) > 1:
        raise Exception("Multiple matches found for starts_with or ends_with. Please use more specific strings.")

    # Ensure starts_with comes before ends_with
    if start_index > end_index:
        raise Exception("'starts_with' must appear before 'ends_with' in the file")

    end_index += len(ends_with)
    new_content = content[:start_index] + text + content[end_index:]

    # Backup the original file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_fname = f"{fname}.{timestamp}.bak"
    shutil.copy2(fname, backup_fname)

    # Write the new content
    with open(fname, 'w') as f:
        f.write(new_content)

    return True

@command()
async def dir(full_path, context=None):
    """List files in directory.
    Parameter: full_path - The full path to the directory to list files in.

    Example:
    
    { "dir": { "full_path": "/path/to/subdir1" } }

    """
    files = os.listdir(full_path)
    print(f'Files in {full_path}: {files}')
    return files

@command()
async def restore(fname, timestamp=None, context=None):
    """Restore a file from its backup. If no timestamp is specified, restore the latest backup.
    Parameters:

    fname - The file to restore.
    timestamp - The specific timestamp of the backup to restore. If omitted, the latest backup will be used.

    Example:

    { "restore": { "fname": "file1.txt", "timestamp": "12_24_11_00_00" } }

    Example (latest backup):

    { "restore": { "fname": "file1.txt" } }

    """
    restore_file(fname, timestamp)
    print(f'Restored {fname} from backup.')

@command()
async def show_backups(context=None):
    """List all backup files in the .backup directory.
    Example:
    { "show_backups": {} }
    """
    backup_dir = '.backup'
    if not os.path.exists(backup_dir):
        print(f"The backup directory {backup_dir} does not exist.")
        return []
    backups = glob.glob(os.path.join(backup_dir, '*'))
    backup_files = [os.path.basename(backup) for backup in backups]
    print(f"Backup files: {backup_files}")
    return backup_files

@command()
async def apply_udiff(abs_root_path, udiff, context=None):
    """
Apply a unified diff to one or more files in a project.

Parameters:
    abs_root_path - The absolute path to the root directory of the project.
                    Files in the diff will be relative to this path.

    udiff         - The unified diff to apply to the file(s).

Write out the changes similar to a unified diff like `diff -U0` would produce.
Use the RAW mode (START_RAW and END_RAW) and don't JSON escape the udiff parameter.

Return edits similar to unified diffs that `diff -U0` would produce.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Don't include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly.

Indentation matters in the diffs!

Start a new hunk for each section of the file that needs changes.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

Be sure to include context lines to avod fragile diffs.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.



To move code within a file, use 2 hunks: 1 to delete it from its current location, 1 to insert it in the new location.

To make a new file, show a diff from `--- /dev/null` to `+++ path/to/new/file.ext`.

Example:

(User request: 'Replace is_prime with a call to sympy.')

{ "apply_udiff": { "abs_root_path": "/path/to/app.py",
                   "udiff": START_RAW
--- mathweb/flask/app.py
+++ mathweb/flask/app.py
@@ ... @@
-class MathWeb:
+import sympy
+
+class MathWeb:
@@ ... @@
-def is_prime(x):
-    if x < 2:
-        return False
-    for i in range(2, int(math.sqrt(x)) + 1):
-        if x % i == 0:
-            return False
-    return True
@@ ... @@
-@app.route('/prime/<int:n>')
-def nth_prime(n):
-    count = 0
-    num = 1
-    while count < n:
-        num += 1
-        if is_prime(num):
-            count += 1
-    return str(num)
+@app.route('/prime/<int:n>')
+def nth_prime(n):
+    count = 0
+    num = 1
+    while count < n:
+        num += 1
+        if sympy.isprime(num):
+            count += 1
+    return str(num)

END_RAW

    }
}


"""
    dir = os.path.dirname(abs_root_path)
    io = FileIO(dir)
    coder = UnifiedDiffCoder(io)
 
    edits = coder.get_edits(udiff)
    num_edits = coder.apply_edits(edits)
    print(f"Applied {num_edits} edits")
    print("Updated content:")
    return f"[SYSTEM command result, NOT user reply: Applied {num_edits} edits. You may wish to read() the file(s) to verify the diff was applied as expected.]"
 
