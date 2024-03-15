# import AES encryption and decryption libs
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import re


# AES encryption func
def encrypt_text_aes(text, key):
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(text.encode(), AES.block_size))
    iv = cipher.iv
    encrypted_text = iv + ct_bytes
    return encrypted_text


# AES decryption func
def decrypt_text_aes(encrypted_text, key):
    iv = encrypted_text[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(encrypted_text[AES.block_size:]), AES.block_size)
    return pt.decode()


# IPv4 address encryption for document
def encrypt_ipv4_addresses(address_mapping, text, key):
    # mapping ipv4 address
    ipv4_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    # find all ipv4 address
    ipv4_addresses = re.findall(ipv4_pattern, text)

    # encrypt every ipv4 address
    for ip in ipv4_addresses:
        encrypted_ip = encrypt_text_aes(ip, key).decode('ISO-8859-1')
        text = text.replace(ip, encrypted_ip)
        address_mapping[encrypted_ip] = ip

    # return
    return address_mapping, text


# private cloud decryption
def decrypt_ipv4_addresses(address_mapping, result):
    for encrypted_ip, original_ip in address_mapping.items():
        result = result.replace(encrypted_ip, original_ip)
    return result
