import ast
import os
import sys

def get_method_bodies(filepath):
    """Parses a file and returns a dictionary mapping ClassName.method_name to its source code."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    lines = content.split('\n')
    methods = {}
    
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    key = f"{node.name}.{item.name}"
                    start = item.lineno - 1
                    end = item.end_lineno
                    methods[key] = '\n'.join(lines[start:end])
        elif isinstance(node, ast.FunctionDef):
            key = node.name
            start = node.lineno - 1
            end = node.end_lineno
            methods[key] = '\n'.join(lines[start:end])
            
    return methods

def compare_logic():
    old_file = 'expenses/views_old.py'
    new_dir = 'expenses/views'
    
    old_methods = get_method_bodies(old_file)
    new_methods = {}
    
    for filename in os.listdir(new_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            path = os.path.join(new_dir, filename)
            new_methods.update(get_method_bodies(path))
            
    # Target classes to check based on user feedback
    targets = ['AnalyticsView', 'CalendarView', 'ExpenseListView', 'ExpenseCreateView', 'ExpenseUpdateView', 'ExpenseDeleteView', 'ExpenseBulkDeleteView', 'ExpenseExportCSV', 'ExpenseExportPDF', 'home_view']
    
    diff_count = 0
    with open('logic_diff.txt', 'w') as out:
        for key, old_code in old_methods.items():
            class_name = key.split('.')[0] if '.' in key else key
            if class_name in targets:
                if key in new_methods:
                    new_code = new_methods[key]
                    # Simple comparison (ignoring whitespace differences might be better, but exact match is a good start)
                    # We will strip leading/trailing whitespace for comparison
                    old_clean = '\n'.join([line.strip() for line in old_code.split('\n') if line.strip()])
                    new_clean = '\n'.join([line.strip() for line in new_code.split('\n') if line.strip()])
                    
                    if old_clean != new_clean:
                        out.write(f"--- LOGIC MISMATCH: {key} ---\n")
                        out.write("OLD CODE:\n")
                        out.write(old_code + "\n\n")
                        out.write("NEW CODE:\n")
                        out.write(new_code + "\n\n")
                        out.write("="*40 + "\n\n")
                        diff_count += 1
                else:
                    out.write(f"--- MISSING METHOD ENTIRELY: {key} ---\n")
                    diff_count += 1
                    
    print(f"Found {diff_count} potential logic mismatches. Check logic_diff.txt")

if __name__ == '__main__':
    compare_logic()
