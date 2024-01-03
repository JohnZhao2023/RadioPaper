import socket
import yaml
from Crypto.Random import get_random_bytes
from EncryptionDecryption import encryption_process, decrypt_ipv4_addresses
import time

# What environment variable can be set to select a different kubeconfig file when running antctl out-of-cluster in "controller mode"?

# private cloud agent in charge of receiving the answer and decrypt it
def private_cloud_server(address_mapping, host='0.0.0.0', port=8000):
    # establish a socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # bind the host private cloud address and port 8000
        s.bind((host, port))
        s.listen()
        # show the information
        print(f"\nSuccess! The private cloud {host} is listening on the port {port}...")
        # receive the connection from the public server
        conn, addr = s.accept()
        with conn:
            # print which public server is connected
            print('\nConnected by', addr)

            # receive the data
            data = conn.recv(1024*1024*8192).decode('utf-8')
            encrypted_answer = data

            # decrypt the answer using the address mapping
            decrypted_answer = decrypt_ipv4_addresses(address_mapping, data)

            # print
            print("\nThe encrypted anwer is:\n", encrypted_answer)
            print("\nThe decrypted anwer is:\n", decrypted_answer)
            # print('Connection closed')


# private cloud agent in charge of generating the question and encrypt it
def private_cloud_client(address_mapping, key,
                         server_host,
                         server_port=8000,
                         private_port=8000):

    # generating the socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # connect the public cloud
        s.connect((server_host, server_port))
        # print the connection success
        print(f"\nconnecting to the public cloud {server_host} succeed!")

        # asking question
        while True:
            # get unencrypted question from the input
            question = input("\nplease input question, input exit to exit:\n")
            # exit
            if question.lower() == 'exit':
                s.sendall('Exit'.encode('utf-8'))
                break

            # timing
            start_time = time.time()

            # encrypt the question
            address_mapping, encrypted_input, encrypted_markdown_content = encryption_process(address_mapping, question, "./antctl.md", key)
            # no encryption
            # loader = TextLoader("./antctl.md")
            # markdown_document = loader.load()
            # encrypted_markdown_content = markdown_document[0].page_content
            # encrypted_input = question

            # data = json.dumps({
            #     "encrypted_question": encrypted_input,
            #     "encrypted_markdown_content": encrypted_markdown_content
            # })
            # sent the encrypted question and references
            data = encrypted_input + "__xxxxx__" + encrypted_markdown_content
            s.sendall(data.encode('utf-8'))
            print("\nthe question is already sent to the public server!")

            # start to listen to the port to get the undecrypted answer
            private_cloud_server(address_mapping, port=private_port)

            # end time
            end_time = time.time()

            # print the time
            print(f"\nThe time for this process is: {end_time - start_time} second")


# main func
if __name__ == "__main__":
    # read yaml file
    with open('private_cloud.yaml', 'r') as file:
        yaml_data = yaml.safe_load(file)

    # get the params
    public_server_addr = yaml_data['properties']['public-server-address']
    public_port = yaml_data['properties']['public-server-port']
    private_port = yaml_data['properties']['private-server-port']

    # forming the key
    key = get_random_bytes(16)

    # address mapping
    address_mapping = {}

    # private cloud
    private_cloud_client(address_mapping, key,
                         server_host=public_server_addr,
                         server_port=public_port,
                         private_port=private_port)