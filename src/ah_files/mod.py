from .make_file_backup import backup_file, restore_file
from lib.providers.commands import command
import os
import glob

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
async def write(fname="", text="", context=None):
    """Write text to a file. Will overwrite the file if it exists.
    Make sure you know the full path first.
    Note: Do NOT use placeholders instead of full source, such as " # ..keep existing code"
          as this will not work and will effectively delete all of that code that was there before.
        All text must be provided to be written to the file.

    Example:
    { "write": { "fname": "/path/to/file1.txt", "text": "This is the text to write to the file.\nLine 2." } }

    Remember: this is JSON, which means that all strings must be properly escaped, such as for newlines, etc. !

    """
    print("Write file, context is:", context, 'context.data is:', context.data)
    if 'current_dir' in context.data:
        if fname.startswith('/') or fname.startswith('./') or fname.startswith('../'):
            fname = fname + ''
        else:
            if 'current_dir' in context.data:
                fname = context.data['current_dir'] + '/' + fname
    
    dirname = os.path.dirname(fname)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    if os.path.isfile(fname):
        backup_file(fname)
    with open(fname, 'w') as f:
        f.write(text)
        print(f'Wrote text to {fname}')
    return True


@command()
async def read(fname="", context=None):
    """Read text from a file.
    You should know the full path.
    Example:
    { "read": { "fname": "/path/to/file1.txt" } }
    """
    if 'current_dir' in context.data:
        if fname.startswith('/') or fname.startswith('./') or fname.startswith('../'):
            fname = fname + ''
        else:
            if 'current_dir' in context.data:
                fname = context.data['current_dir'] + '/' + fname
    else:
        print('No current_dir in context.data')
        print('context.data=', context.data)

    print('context=', context, 'fname=', fname)
    print('context.data = ', context.data)
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
async def dir(directory='', context=None):
    """List files in directory.
    Parameter: directory - The directory to list files in. If empty, lists files in the current directory.

    Example:
    
    { "dir": "/path/to/subdir1" }

    Other Example (current dir)

    { "dir": "" }

    """
    if directory.startswith('/') or directory.startswith('./') or directory.startswith('../'):
        directory = directory + ''
    else:
        if 'current_dir' in context.data:
            directory = context.data['current_dir'] + '/' + directory
    files = os.listdir(directory)
    print(f'Files in {directory}: {files}')
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
    if 'current_dir' in context.data:
        fname = context.data['current_dir'] + '/' + fname
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
async def cd(directory, context=None):
    """Change the current working directory.

    Parameter: directory - The directory to change to. This can be a relative or absolute path.
                           If unsure, use absolute path.

    Example:

    { "cd": "subdir1" }

    Other Example (parent dir)

    { "cd": ".." }

    """
    if 'current_dir' not in context.data:
        context.data['current_dir'] = os.getcwd()
    if directory.startswith('/'):
        new_dir = directory
    else:
        new_dir = os.path.realpath(os.path.join(context.data['current_dir'], directory))
    if os.path.isdir(new_dir):
        context.data['current_dir'] = new_dir
        context.save_context()
        print(f'Changed current directory to {new_dir}')
    else:
        print(f'Directory {new_dir} does not exist.')
    return True
