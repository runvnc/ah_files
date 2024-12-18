from .make_file_backup import backup_file, restore_file
from lib.providers.commands import command
import os
import glob
import json
from datetime import datetime
import shutil
from .numbered import numbered_file_to_string, replace_lines_impl


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
    """Write text to a file. Will overwrite the file if it exists.
    Make sure you know the full path first.
    Note: All text must be provided to be written to the file. Do NOT include placeholders,
    as the text will be written exactly as provided.

    For large amounts of text, use append() with multiple commands.

    fname MUST be the absolute path to the file.

    Use the RAW string block encoding for the text parameter.

    Example:

    { "write": { "fname": "/path/to/file1.txt",
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

    if os.path.isfile(fname):
        backup_file(fname)
    
    with open(fname, 'w') as f:
        f.write(text)
    
    print(f'Wrote text to {fname}')
    return True

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
async def dir(dir='', context=None):
    """List files in directory.
    Parameter: dir - The full path to the directory to list files in.

    Example:
    
    { "dir": "/path/to/subdir1" }

    """
    files = os.listdir(dir)
    print(f'Files in {dir}: {files}')
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

ignore ="""
#@command()
#async def cd(dir, context=None):
#    Change the current working directory.

    #    Parameter: directory - The directory to change to. This can be a relative or absolute path.
                           If unsure, use absolute path.

    #    Example:

    { "cd": "subdir1" }

    Other Example (parent dir)

    { "cd": ".." }

    new_dir = os.path.abspath(dir)
    if os.path.isdir(new_dir):
        context.data['current_directory'] = new_dir
        print(f'Changed current directory to {new_dir}')
    else:
        print(f'Directory {new_dir} does not exist.')
    return True
"""

@command()
async def read_numbered(fname, context=None):
    """Read a file and return its contents as a numbered string.

    Parameters:
    fname (str): The absolute path to the file to be read.

    Returns:
    str: A string containing the file contents with line numbers.

    Example:
    { "read_numbered": { "fname": "/path/to/file.txt" } }
    """
    result = numbered_file_to_string(fname)
    print(f'Read numbered content from {fname}')
    return result

@command()
async def replace_lines(fname, start, end, new_text, context=None):
    """Replace text in a file from the start line number to the end line number with new text.

    Parameters:
    fname (str): The absolute path to the file to be modified.
    start (int): The starting line number (1-indexed).
    end (int): The ending line number (1-indexed).
    new_text (RAW str): The text to insert, replacing the original text. This does not need to match the original line count.
                        To delete text, use a blank line here.
                    
    Returns:

    bool: True if successful, False otherwise.

    Example:
    { "replace_lines": { 
        "fname": "/path/to/file.txt",
        "start": 3,
        "end": 5,
        "new_text": START_RAW 
    This is a new line
    And another one
    Third line
    END_RAW
    } }

    """
    result = replace_lines_impl(fname, start, end, new_text)
    if result:
        print(f'Successfully replaced lines {start} to {end} in {fname}')
    else:
        print(f'Failed to replace lines in {fname}')
    return result

