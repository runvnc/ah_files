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
                    Use RAW mode with START_RAW and END_RAW for the diff content.

Best Practices:
    1. Make one logical change at a time - don't combine multiple conceptual changes
       in a single diff. Each diff should represent one coherent modification.

    2. Include sufficient unique context around changes - use function/class boundaries
       or other distinctive sections to ensure correct placement.

    3. When modifying a file multiple times, verify each change before proceeding
       to the next change. Don't try to make multiple changes in one diff.

    4. Ensure proper marking of removed (-) and added (+) lines, and include
       enough unchanged context lines (starting with space) around the changes.

    5. When editing a function or class, replace the entire block to maintain
       consistency - remove the old version with (-) lines then add the new
       version with (+) lines.

Technical Notes:
    - Include the first 2 lines with file paths (--- and +++ lines)
    - Start each change section with @@ ... @@ line
    - Use /dev/null as source path for new files
    - Indentation must match exactly
    - To move code, use separate remove and add hunks

Example:

    { "apply_udiff": { "abs_root_path": "/path/to/project",
                      "udiff": START_RAW
    --- example.py
    +++ example.py
    @@ -1,3 +1,3 @@
    -def old_function():
    -    return 'old'
    +def new_function():
    +    return 'new'
    END_RAW
    }}
    """
    io = FileIO(abs_root_path)
    coder = UnifiedDiffCoder(io)
 
    edits = coder.get_edits(udiff)
    print("Num edits found:", len(edits))
    num_edits = coder.apply_edits(edits)
    print(f"Applied {num_edits} edits")
    print("Updated content:")
    return f"[SYSTEM command result, NOT user reply: Found edits: {str(edits)}.  Applied {num_edits} edits. You may wish to read() the file(s) to verify the diff was applied as expected.]"
