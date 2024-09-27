#!/bin/bash

# 检查sessions目录是否存在
if [ ! -d "sessions" ]; then
    echo "Error: sessions directory not found"
    exit 1
fi

# 读取error.txt文件,提取电话号码
while IFS='|' read -r phone _; do
    # 移除电话号码前的'+'号(如果存在)
    phone=${phone#+}
    
    # 在sessions目录中查找并删除对应的文件
    find sessions -type f -name "*$phone*" -delete
    
    # 输出删除操作的结果
    if [ $? -eq 0 ]; then
        echo "Deleted session file for $phone"
    else
        echo "No session file found for $phone"
    fi
done < error.txt

echo "Session deletion process completed"