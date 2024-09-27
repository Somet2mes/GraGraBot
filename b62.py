import re

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def address_to_base62(address: str) -> str:
    if not re.match(r'^0x[0-9a-fA-F]{40}$', address):
        raise ValueError("Invalid Ethereum address format")
    
    decimal = int(address[2:], 16)
    result = ""
    while decimal > 0:
        result = BASE62[decimal % 62] + result
        decimal //= 62
    
    return result.zfill(27)  # Pad to 27 characters

def base62_to_address(base62: str) -> str:
    if not re.match(r'^[0-9A-Za-z]{27}$', base62):
        raise ValueError("Invalid Base62 string format")
    
    decimal = 0
    for char in base62:
        decimal = decimal * 62 + BASE62.index(char)
    
    hex_address = hex(decimal)[2:].zfill(40)
    return f"0x{hex_address}"

print(base62_to_address(input()))
