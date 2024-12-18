def numbered_file_to_string(file_path):
    """
    Reads a file and converts it to a string with line numbers at the start.
    
    Args:
    file_path (str): The path to the file to be read.
    
    Returns:
    str: A string containing the file contents with line numbers.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        
        max_line_num = len(lines)
        line_num_width = len(str(max_line_num))
        
        numbered_lines = [f"{i+1:>{line_num_width}}| {line}" for i, line in enumerate(lines)]
        return ''.join(numbered_lines)
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def replace_lines_impl(file_path, start, end, new_lines):
    """
    Replaces lines in a file from the start line number to the end line number with new lines.

    Args:
    file_path (str): The path to the file to be modified.
    start (int): The starting line number (1-indexed).
    end (int): The ending line number (1-indexed).
    new_lines (list): A list of strings to replace the original lines.

    Returns:
    bool: True if successful, False otherwise.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Check if start and end are valid
        if start < 1 or end > len(lines) or start > end:
            return False

        # Replace the lines
        lines[start-1:end] = new_lines

        # Write the modified content back to the file
        with open(file_path, 'w') as file:
            file.writelines(lines)

        return True
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return False
    except Exception as e:
        print(f"Error modifying file: {str(e)}")
        return False


if __name__ == '__main__':
    file_path = 'test_numbered.txt'
    with open(file_path, 'w') as file:
        file.write('This is a line\n')
        file.write('This is another line\n')
        file.write('This is a third line\n')
        file.write('This is a fourth line\n')
        file.write('This is a fifth line\n')

    print(numbered_file_to_string(file_path))
    
    new_lines = ['This is a new line\n', 'This is another new line\n']
    if replace_lines_impl(file_path, 2, 4, new_lines):
        print(numbered_file_to_string(file_path))

