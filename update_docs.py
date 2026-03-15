import ast
from pathlib import Path

for path in Path('backend/app').rglob('*.py'):
    try:
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        insertions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not ast.get_docstring(node):
                insertions.append({
                    'line': getattr(node.body[0], 'lineno', 1) - 1, 
                    'name': node.name, 
                    'col': getattr(node.body[0], 'col_offset', 4)
                })
        if insertions:
            lines = source.split('\n')
            insertions.sort(key=lambda x: x['line'], reverse=True)
            for ins in insertions:
                name = ins['name']
                indent = ' ' * ins['col']
                desc = f"处理 {name.replace('_', ' ')} 请求或相关逻辑。"
                if name.startswith('get_'): desc = f"获取 {name[4:].replace('_', ' ')} 相关数据。"
                if name.startswith('list_'): desc = f"获取 {name[5:].replace('_', ' ')} 列表。"
                if name.startswith('create_'): desc = f"创建新的 {name[7:].replace('_', ' ')}。"
                if name.startswith('update_'): desc = f"更新已有的 {name[7:].replace('_', ' ')}。"
                if name.startswith('delete_'): desc = f"删除指定的 {name[7:].replace('_', ' ')}。"
                if name.startswith('_serialize'): desc = f"内部辅助函数：序列化 {name[11:].replace('_', ' ')}。"
                doc = f'{indent}"""\n{indent}{desc}\n{indent}"""'
                lines.insert(ins['line'], doc)
            path.write_text('\n'.join(lines), encoding='utf-8')
            print(f'Updated {path}')
    except Exception as e:
        print(f'Error on {path}: {e}')
