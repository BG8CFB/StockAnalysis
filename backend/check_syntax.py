#!/usr/bin/env python
"""临时脚本：检查修改文件的语法"""
import ast
import sys

files_to_check = [
    'E:/Code/StockAnalysis/backend/modules/trading_agents/core/agent_engine.py',
    'E:/Code/StockAnalysis/backend/modules/mcp/config/loader.py',
    'E:/Code/StockAnalysis/backend/modules/mcp/core/adapter.py',
]

all_ok = True
for filepath in files_to_check:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print(f"✓ {filepath}: 语法正确")
    except SyntaxError as e:
        print(f"✗ {filepath}: 语法错误")
        print(f"  行 {e.lineno}: {e.msg}")
        all_ok = False
    except Exception as e:
        print(f"✗ {filepath}: {e}")
        all_ok = False

if all_ok:
    print("\n所有文件语法检查通过！")
    sys.exit(0)
else:
    print("\n发现语法错误！")
    sys.exit(1)
