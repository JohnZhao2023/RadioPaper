import socket
from Crypto.Random import get_random_bytes
from EncryptionDecryption import encryption_process, decrypt_ipv4_addresses
import time
from langchain.document_loaders import TextLoader


# private cloud agent in charge of receiving the answer and decrypt it
def private_cloud_server(address_mapping, host='xx.xx.xx.xx', port=8000):
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
            # no decryption
            # decrypted_answer = encrypted_answer

            # print
            print("\nThe encrypted anwer is:\n", encrypted_answer)
            print("\nThe decrypted anwer is:\n", decrypted_answer)
            # print('Connection closed')


# private cloud agent in charge of generating the question and encrypt it
def private_cloud_client(address_mapping, key,
                         server_host='xx.xx.xx.xx', server_port=8000):

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
            private_cloud_server(address_mapping)

            # end time
            end_time = time.time()

            # print the time
            print(f"\nThe time for this process is: {end_time - start_time} second")


# main func
if __name__ == "__main__":
    # forming the key
    key = get_random_bytes(16)

    # address mapping
    address_mapping = {}

    # private cloud
    private_cloud_client(address_mapping, key)
