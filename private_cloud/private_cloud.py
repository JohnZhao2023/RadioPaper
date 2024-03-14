# import the relevant libraries
import socket
import yaml
from Crypto.Random import get_random_bytes
from EncryptionDecryption import decrypt_ipv4_addresses, encrypt_ipv4_addresses
from langchain.vectorstores import FAISS
from langchain.embeddings import CacheBackedEmbeddings, ModelScopeEmbeddings
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.storage import LocalFileStore
from langchain.document_loaders import TextLoader
import time
import os


# check whether the specific dir is in the directory
# for checking if there has already been a local vector store
def check_for_data_directory(dir_name):
    current_directory = os.getcwd()
    directories = os.listdir(current_directory)

    for directory in directories:
        if os.path.isdir(os.path.join(current_directory, directory)) and dir_name in directory:
            return True
    return False


# embedding the whole content and generate local vector store 
def generate_knowledge_base_embeddings(encrypted_markdown_content, cached_embedder):
    # header setting
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]

    # split the text
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(encrypted_markdown_content)

    # local vector store generation
    vectorstore = FAISS.from_documents(md_header_splits, cached_embedder)
    vectorstore.save_local("faiss_index")
    return vectorstore


# private cloud agent in charge of receiving the answer and decrypt it
def private_cloud_server(address_mapping, host='0.0.0.0', port=8000):
    # establish a socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # bind the host private cloud address and port 8000
        s.bind((host, port))
        s.listen()
        # show the information
        print(f"\tSuccess! The private cloud {host} is listening on the port {port}...")
        # receive the connection from the public server
        conn, addr = s.accept()
        with conn:
            # print which public server is connected
            print('\tConnected by', addr)

            # receive the data
            data = conn.recv(1024*1024*8192).decode('utf-8')

            index = data.find("ROUGE-1 Score:")
            encrypted_answer = data[:index]
            rouge_score = float(data[index+14:])

            # decrypt the answer using the address mapping
            decrypted_answer = decrypt_ipv4_addresses(address_mapping, encrypted_answer)

            # print
            print("\n\tThe encrypted anwer is:\n\t", encrypted_answer)
            print("\tThe decrypted anwer is:\n\t", decrypted_answer)
            print("\tThe Rouge-1 Score is: ", rouge_score)
            # print('Connection closed')


# private cloud agent in charge of generating the question and encrypt it
def private_cloud_client(address_mapping, key, knowledge_file_path,
                         server_host,
                         server_port=8000,
                         private_port=8000):

    # encrypt the question
    loader = TextLoader(knowledge_file_path)
    markdown_document = loader.load()
    address_mapping, encrypted_markdown_content = encrypt_ipv4_addresses(address_mapping, markdown_document[0].page_content, key)

    # embedding setting
    underlying_embeddings = ModelScopeEmbeddings()
    store = LocalFileStore("./cache/")
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        underlying_embeddings, store
    )

    # check if the local vector store already exists
    # if exists, then load it, otherwise do the embedding procedure
    if check_for_data_directory("faiss_index"):
        vectorstore = FAISS.load_local("faiss_index",
                                       cached_embedder,
                                       allow_dangerous_deserialization=True)
    else:
        vectorstore = generate_knowledge_base_embeddings(
            encrypted_markdown_content,
            cached_embedder)

    # generating the socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # connect the public cloud
        s.connect((server_host, server_port))
        # print the connection success
        print(f"\nconnecting to the public cloud {server_host} succeed!")

        # question count
        question_count = 1

        # asking question
        while True:
            # get unencrypted question from the input
            question = input(f"\nplease input No.{question_count} question, input exit to exit:\n")
            # exit
            if question.lower() == 'exit':
                s.sendall('Exit'.encode('utf-8'))
                break

            # timing
            start_time = time.time()

            # encrypt the question
            address_mapping, encrypted_input = encrypt_ipv4_addresses(address_mapping, question, key)

            # do the similarity search from the vector store and get the relevant context
            docs = vectorstore.similarity_search(question)
            context = docs[0].page_content

            # conbine the data and send
            data = encrypted_input + "__xxxxx__" + context
            s.sendall(data.encode('utf-8'))
            print("\n\tthe question is already sent to the public server!")

            # start to listen to the port to get the undecrypted answer
            private_cloud_server(address_mapping, port=private_port)

            # end time
            end_time = time.time()

            # print the time
            print(f"\n\tThe time for this process is: {end_time - start_time} second")

            # add the count
            question_count = question_count + 1

        # print end information
        print('Service is closed')


# main func
if __name__ == "__main__":
    # read yaml file
    with open('private_cloud.yaml', 'r') as file:
        yaml_data = yaml.safe_load(file)

    # get the params
    public_server_addr = yaml_data['properties']['public-server-address']
    public_port = yaml_data['properties']['public-server-port']
    private_port = yaml_data['properties']['private-server-port']
    knowledge_file_path = yaml_data['properties']['knowledge-file-path']

    # forming the key
    key = get_random_bytes(16)

    # address mapping
    address_mapping = {}

    # private cloud
    private_cloud_client(address_mapping, key, knowledge_file_path,
                         server_host=public_server_addr,
                         server_port=public_port,
                         private_port=private_port)
