# Import required libraries
import socket
import yaml
from Crypto.Random import get_random_bytes
from EncryptionDecryption import encryption_process, decrypt_ipv4_addresses
import time
import pandas as pd

# Read configuration file
with open('private_cloud.yaml', 'r') as file:
    yaml_data = yaml.safe_load(file)

# Get parameters
public_server_addr = yaml_data['properties']['public-server-address']
public_port = yaml_data['properties']['public-server-port']
private_port = yaml_data['properties']['private-server-port']

# Generate a random key
key = get_random_bytes(16)

# Address mapping for encryption/decryption
address_mapping = {}

# Read the CSV file containing questions
questions_df = pd.read_csv('/path/to/your/questions/file.csv')  # Replace with the path to your questions CSV file

# Private cloud server for receiving answers and ROUGE-1 scores
def private_cloud_server(address_mapping, host='0.0.0.0', port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Success! The private cloud {host} is listening on the port {port}...")

        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            data = conn.recv(1024*1024*8192).decode('utf-8')

            # Assuming encrypted answers and ROUGE-1 scores are in 'data'
            decrypted_answer = decrypt_ipv4_addresses(address_mapping, data)  # Use your decryption method
            print("\nDecrypted Answer:\n", decrypted_answer)

# Private cloud client for generating and sending encrypted questions
def private_cloud_client(address_mapping, key, server_host, server_port=8000, private_port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_host, server_port))
        print(f"Connecting to the public cloud {server_host} succeeded!")

        for index, row in questions_df.iterrows():
            question = row['question']
            encrypted_input, encrypted_markdown_content = encryption_process(address_mapping, question, "./antctl.md", key)

            data = encrypted_input + "__xxxxx__" + encrypted_markdown_content
            s.sendall(data.encode('utf-8'))
            print(f"Question {index+1} sent to the public server.")

            # Start listening on the port to get the decrypted answer and ROUGE-1 score
            private_cloud_server(address_mapping, port=private_port)

if __name__ == "__main__":
    private_cloud_client(address_mapping, key, server_host=public_server_addr, server_port=public_port, private_port=private_port)
