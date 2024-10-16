from .backup_file import backup_file
from lib.providers.commands import command
import os
from .backup_file import restore_file
import glob
import json
from datetime import datetime
import shutil

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
    { "append": { "fname": "/path/to/file1.txt", "text": "This is the text to append to the file.\nLine 2." } }
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

    Example:
    { "write": { "fname": "/path/to/file1.txt", "text": "This is the text to write to the file.\nLine 2." } }

    Remember: this is JSON, which means that all strings in parameter text must be properly escaped, 
    such as for newlines, etc. !!

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
