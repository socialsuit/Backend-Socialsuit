#!/usr/bin/env python3
"""
Script to fix import paths by removing 'social_suit.' prefix
"""
import os
import re

def fix_imports_in_file(file_path):
    """Fix imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace 'from social_suit.app' with 'from app'
        updated_content = re.sub(r'from social_suit\.app', 'from app', content)
        
        # Replace 'import social_suit.app' with 'import app'
        updated_content = re.sub(r'import social_suit\.app', 'import app', updated_content)
        
        # Only write if content changed
        if updated_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"Fixed imports in: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_all_imports():
    """Fix imports in all Python files"""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    fixed_count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        if any(skip_dir in root for skip_dir in ['.git', '__pycache__', '.pytest_cache', 'venv', 'env']):
            continue
            
        for file in files:
            if file.endswith('.py') and file != 'fix_imports.py':
                file_path = os.path.join(root, file)
                if fix_imports_in_file(file_path):
                    fixed_count += 1
    
    print(f"\nFixed imports in {fixed_count} files")

if __name__ == "__main__":
    fix_all_imports()