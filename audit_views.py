import ast
import os
import sys

def get_definitions(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    classes = {}
    functions = []
    
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            classes[node.name] = methods
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
            
    return classes, functions

old_classes, old_functions = get_definitions('expenses/views_old.py')

new_views_dir = 'expenses/views'
new_classes = {}
new_functions = []

for filename in os.listdir(new_views_dir):
    if filename.endswith('.py') and filename != '__init__.py':
        path = os.path.join(new_views_dir, filename)
        cls, fns = get_definitions(path)
        new_classes.update(cls)
        new_functions.extend(fns)

print("--- MISSING CLASSES ---")
for cls_name in old_classes:
    if cls_name not in new_classes:
        print(f"Missing Class: {cls_name}")

print("\n--- MISSING FUNCTIONS ---")
for fn in old_functions:
    if fn not in new_functions:
        print(f"Missing Function: {fn}")
        
print("\n--- MISSING METHODS ---")
for cls_name, methods in old_classes.items():
    if cls_name in new_classes:
        new_methods = new_classes[cls_name]
        for m in methods:
            if m not in new_methods:
                print(f"Missing method in {cls_name}: {m}")

