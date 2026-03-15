import ast
import glob

def generate_doc(name):
    return f'"""\n    执行 {name} 相关的操作及处理。\n    """'

def insert_docstrings(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        
        insertions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    insertions.append({
                        'line': node.body[0].lineno - 1, 
                        'name': node.name,
                        'col': node.body[0].col_offset
                    })
        
        if not insertions: return
            
        lines = source.split('\n')
        insertions.sort(key=lambda x: x['line'], reverse=True)
        
        for ins in insertions:
            name = ins['name']
            indent = " " * ins['col']
            
            # Simple heuristic mapping for some common functions
            desc = f"处理 {name.replace('_', ' ')} 请求并返回结果"
            if name.startswith('get_'): desc = f"获取 {name[4:].replace('_', ' ')} 相关数据"
            if name.startswith('list_'): desc = f"列出 {name[5:].replace('_', ' ')} 的数据列表"
            if name.startswith('create_'): desc = f"创建新的 {name[7:].replace('_', ' ')} 记录"
            if name.startswith('update_'): desc = f"更新已有的 {name[7:].replace('_', ' ')} 记录"
            if name.startswith('delete_'): desc = f"删除指定的 {name[7:].replace('_', ' ')} 记录"
            if name.startswith('_serialize'): desc = f"序列化 {name[11:].replace('_', ' ')} 对象为字典"
            
            doc = f'{indent}"""\n{indent}{desc}。\n{indent}"""'
            lines.insert(ins['line'], doc)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"Updated {filepath}")
    except Exception as e:
        print(e)

for f in glob.glob('backend/app/**/*.py', recursive=True):
    insert_docstrings(f)
