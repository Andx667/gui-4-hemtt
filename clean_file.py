"""Clean the hemtt_gui.py file by removing old tkinter dialog code."""

# Read the file
with open('hemtt_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Keep everything up to and including line 770 (index 769)
good_lines = lines[:770]

# Add the if __name__ block
good_lines.append('\n')
good_lines.append('\n')
good_lines.append('if __name__ == "__main__":\n')
good_lines.append('    main()\n')

# Write back
with open('hemtt_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(good_lines)

print('File cleaned successfully! Removed old tkinter dialog code.')
print(f'New file has {len(good_lines)} lines (was {len(lines)} lines)')
