import json
import requests
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import ast
import time

# 读取wallet.json文件
def read_wallet_addresses():
    addresses = []
    with open('wallet.json', 'r') as file:
        for line in file:
            if line.strip():
                wallet_data = ast.literal_eval(line.strip())
                addresses.append(wallet_data['address'])
            else:
                continue
    return addresses

# 读取代理列表
def read_proxies():
    proxies = []
    with open('bot/config/proxies.txt', 'r') as file:
        for line in file:
            proxy = line.strip().split("http://")[1]
            parts = proxy.split(':')
            if len(parts) == 4:
                proxies.append({
                    'http': f'http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}',
                    'https': f'http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}'
                })
    return proxies

# 获取钱包余额
def get_wallet_balance(address, proxies):
    url = f"https://wl-api.gra.fun/api/status/{address}"
    
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control': 'no-cache',
        'origin': 'https://gra.fun',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://gra.fun/',
        'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Microsoft Edge";v="128"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0'
    }

    try:
        if not proxies:
            raise ValueError("代理列表为空")
        
        proxy = random.choice(proxies)
        response = requests.get(url, headers=headers, proxies=proxy, timeout=10)
        print(response.text)
        if response.status_code == 200 and response.text.find("user_id") != -1:
            data = response.json()
            user_id=data.get("user_id")
            wallet_address = data.get('wallet_address', 'Unknown')
            balance = data.get('offchain_points', 'Unknown')
            if balance == 900 or balance == 800 or balance == 700  :
                with open('sum.txt', 'a') as file:
                    file.write(f"{user_id}-{wallet_address}-{balance}\n")
        return f"无法获取地址 {address} 的余额信息"
    except Exception as e:
        return f"请求失败 {address}: {str(e)}"

# 主函数
def main():
    addresses = read_wallet_addresses()
    proxies = read_proxies()
    
    if not proxies:
        print("警告：代理列表为空。请检查 bot/config/proxies.txt 文件。")
        return

    # 设置并发数，可以根据需要调整
    max_workers = min(10, len(proxies))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_address = {executor.submit(get_wallet_balance, address, proxies): address for address in addresses}


if __name__ == "__main__":
    main()