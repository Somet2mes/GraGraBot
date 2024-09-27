# 读取文件并过滤行
with open('stat.json', 'r') as file:
    lines = file.readlines()

# 过滤掉不包含 '| 900' 或 '| 800' 的行
filtered_lines = [line for line in lines if '| 900' in line or '| 800' in line]

# 将过滤后的行写回文件
with open('stat.json', 'w') as file:
    file.writelines(filtered_lines)