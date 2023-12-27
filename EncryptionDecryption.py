# import AES encryption and decryption libs
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import re
from langchain.document_loaders import TextLoader


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

# # private cloud decryption
# def decrypt_ipv4_addresses(address_mapping, result, key):
#     # mapping ipv4 address
#     ipv4_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
#     ipv4_addresses = re.findall(ipv4_pattern, result)

#     for encrypted_pii in ipv4_addresses:
#         pii = decrypt_text_aes(encrypted_pii.encode('ISO-8859-1'), key)
#         result = result.replace(encrypted_pii, pii)
#     return result


# private cloud decryption
def decrypt_ipv4_addresses(address_mapping, result):
    for encrypted_ip, original_ip in address_mapping.items():
        result = result.replace(encrypted_ip, original_ip)
    return result


# encryption process
def encryption_process(address_mapping, input_string, document_path, key):
    # encrypt ipv4 address in the question
    address_mapping, encrypted_input = \
                    encrypt_ipv4_addresses(address_mapping, input_string, key)
    # encrypt ipv4 address in the reference document
    loader = TextLoader(document_path)
    markdown_document = loader.load()
    address_mapping, encrypted_markdown_content = encrypt_ipv4_addresses(address_mapping, markdown_document[0].page_content, key)
    # return the encrypted question and encrypted content
    return address_mapping, encrypted_input, encrypted_markdown_content
