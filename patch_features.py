import ast
import traceback

def extract_method_source(filepath, target_class, target_method):
    with open(filepath, 'r') as f:
        content = f.read()
    tree = ast.parse(content)
    lines = content.split('\n')
    
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == target_class:
            for m in node.body:
                if isinstance(m, ast.FunctionDef) and m.name == target_method:
                    start = getattr(m, 'decorator_list', [m])[0].lineno - 1 if m.decorator_list else m.lineno - 1
                    end = m.end_lineno
                    return '\n'.join(lines[start:end])
        elif target_class is None and isinstance(node, ast.FunctionDef) and node.name == target_method:
            start = getattr(node, 'decorator_list', [node])[0].lineno - 1 if node.decorator_list else node.lineno - 1
            end = node.end_lineno
            return '\n'.join(lines[start:end])
    return None

def extract_method_range(filepath, target_class, target_method):
    with open(filepath, 'r') as f:
        content = f.read()
    tree = ast.parse(content)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == target_class:
            for m in node.body:
                if isinstance(m, ast.FunctionDef) and m.name == target_method:
                    start = getattr(m, 'decorator_list', [m])[0].lineno - 1 if m.decorator_list else m.lineno - 1
                    return start, m.end_lineno
        elif target_class is None and isinstance(node, ast.FunctionDef) and node.name == target_method:
            start = getattr(node, 'decorator_list', [node])[0].lineno - 1 if node.decorator_list else node.lineno - 1
            return start, node.end_lineno
    return None, None

def replace_logic(old_file, new_file, target_class, target_method):
    old_code = extract_method_source(old_file, target_class, target_method)
    if not old_code:
        print(f"Failed to extract {target_class}.{target_method} from {old_file}")
        return

    start, end = extract_method_range(new_file, target_class, target_method)
    if start is None:
        print(f"Failed to find {target_class}.{target_method} in {new_file}")
        return

    with open(new_file, 'r') as f:
        lines = f.readlines()
    
    new_content = ''.join(lines[:start]) + old_code + '\n' + ''.join(lines[end:])
    
    with open(new_file, 'w') as f:
        f.write(new_content)
    print(f"Replaced {target_class}.{target_method} in {new_file}")

patches = [
    ('expenses/views_old.py', 'expenses/views/misc.py', None, 'upload_view'),
    ('expenses/views_old.py', 'expenses/views/dashboard.py', 'BudgetDashboardView', 'get_context_data'),
    ('expenses/views_old.py', 'expenses/views/expenses.py', 'ExpenseBulkUpdateView', 'post'),
    ('expenses/views_old.py', 'expenses/views/recurring.py', 'RecurringTransactionListView', 'get_queryset'),
    ('expenses/views_old.py', 'expenses/views/recurring.py', 'RecurringTransactionListView', 'get_context_data')
]

for old_f, new_f, cls, meth in patches:
    replace_logic(old_f, new_f, cls, meth)
