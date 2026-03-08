import ast

def get_missing_source(filepath, target_classes):
    with open(filepath, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    lines = content.split('\n')
    
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in target_classes:
            methods_to_find = target_classes[node.name]
            for m in node.body:
                if isinstance(m, ast.FunctionDef) and m.name in methods_to_find:
                    start = m.lineno - 1
                    end = m.end_lineno
                    print(f"--- {node.name}.{m.name} ---")
                    print('\n'.join(lines[start:end]))
                    print()

missing_map = {
    'ExpenseUpdateView': ['get_success_url', 'get_context_data'],
    'CategoryCreateView': ['get_context_data'],
    'CategoryUpdateView': ['get_context_data', 'get_success_url', 'form_valid'],
    'IncomeListView': ['get_context_data'],
    'IncomeCreateView': ['get_success_url', 'get_context_data'],
    'IncomeUpdateView': ['get_success_url', 'get_context_data', 'form_valid'],
    'RecurringTransactionCreateView': ['get_success_url', 'get_context_data'],
    'RecurringTransactionUpdateView': ['get_success_url', 'get_context_data', 'get_queryset'],
    'RecurringTransactionDeleteView': ['form_valid'],
    'ContactView': ['_get_client_ip', '_check_rate_limit', '_is_spam_content', '_is_disposable_email'],
    'SavingsGoalUpdateView': ['get_queryset', 'form_valid'],
    'SavingsGoalDeleteView': ['delete'],
    'YearInReviewView': ['dispatch']
}

get_missing_source('expenses/views_old.py', missing_map)
