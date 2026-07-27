content = open('main.py', encoding='utf-8').read()
old = '    "capacity_risk", "advanced_intelligence", "tender_docs",'
new = '    "capacity_risk", "advanced_intelligence", "advanced_analytics", "tender_docs",'
if old in content:
    content = content.replace(old, new)
    open('main.py', 'w', encoding='utf-8').write(content)
    print('Updated main.py - added advanced_analytics')
else:
    print('Pattern not found, trying alternate...')
    # Try to find the line
    for i, line in enumerate(content.split('\n')):
        if 'capacity_risk' in line and 'advanced_intelligence' in line:
            print(f'Found at line {i+1}: {repr(line)}')
