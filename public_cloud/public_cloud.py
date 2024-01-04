# import the lib with ChatGPT model and relevant libs
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
import socket
import yaml
import time

# get the global setting of the params
# read yaml file
with open('public_cloud.yaml', 'r') as file:
    yaml_data = yaml.safe_load(file)

# get the params
open_api_key_yaml = yaml_data['properties']['openai_api_key']
public_port = yaml_data['properties']['public-server-port']
private_port = yaml_data['properties']['private-server-port']

# cache settings
underlying_embeddings = OpenAIEmbeddings(openai_api_key=open_api_key_yaml)
store = LocalFileStore("./cache/")
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings, store, namespace=underlying_embeddings.model
)


# the agent in charge of sending the undecrypted answer to the private cloud
def send_answer_to_private_cloud(encrypted_answer, private_cloud_host, private_cloud_port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # connect to the private cloud
        s.connect((private_cloud_host, private_cloud_port))

        # print the connection success info
        print(f"connecting to the private cloud {private_cloud_host} succeed!")

        # send the undecrypted answer
        s.sendall(encrypted_answer.encode('utf-8'))


# agent in charge of receiving the question and begin RAG process
def public_cloud_server(open_api_key_yaml,
                        public_port=8000,
                        private_port=8000,
                        host='0.0.0.0'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # bind the agent on the port to receive the question
        s.bind((host, public_port))
        s.listen()

        # print the info of the success of the listening to the port
        print(f"Success! The {host} is listening on the port {public_port}...")

        # connected by the private cloud
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            # constantly receive the data from the private cloud
            while True:
                # receive the data
                data = conn.recv(1024*1024*16384).decode('utf-8')

                # if data is empty
                if not data or len(data) < 1:
                    data = []
                    continue

                # find the segment tag, if not find then it's not normal data
                index = data.find("__xxxxx__")
                if index == -1:
                    data = []
                    continue

                # extract the question and the content
                encrypted_question = data[:index]
                encrypted_markdown_content = data[index+9:]
                if len(encrypted_question) > 8192:
                    encrypted_question = encrypted_question[:8192]

                # check the cache

                # start the time counting
                start_RAG_time = time.time()

                # start RAG process
                # data pre-processing
                headers_to_split_on = [
                    ("#", "Header 1"),
                    ("##", "Header 2"),
                    ("###", "Header 3"),
                    ("####", "Header 4"),
                ]
                markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
                md_header_splits = markdown_splitter.split_text(encrypted_markdown_content)

                # start retriever time
                start_retriever_time = time.time()

                # retriever setting
                retriever = FAISS.from_documents(md_header_splits, cached_embedder).as_retriever(search_kwargs={"k": 2})

                # end retriever time
                end_retriever_time = time.time()

                # print
                # print the time
                print(f"\tThe time for retriever process is: {end_retriever_time - start_retriever_time} second")

                # model setting
                open_api_key = open_api_key_yaml
                template = """How to use antctl command without bash character to implement question based only on the following context:
                    {context}

                Question: {question}
                    """
                prompt = ChatPromptTemplate.from_template(template)
                # model = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=open_api_key)
                model = ChatOpenAI(model_name="gpt-4", openai_api_key=open_api_key)
                output_parser = StrOutputParser()
                setup_and_retrieval = RunnableParallel(
                    {"context": retriever, "question": RunnablePassthrough()}
                )

                # RAG
                chain = setup_and_retrieval | prompt | model | output_parser
                encrypted_answer = chain.invoke(encrypted_question)

                # finish time counting
                end_RAG_time = time.time()

                # print the time
                print(f"\tThe time for RAG process is: {end_RAG_time - start_RAG_time} second")

                # send the encrypted answer to the private cloud
                if not encrypted_answer:
                    continue
                send_answer_to_private_cloud(encrypted_answer,
                                             private_cloud_host=addr[0],
                                             private_cloud_port=private_port)

                # clean data
                data = []

            # print('Connection closed')


# main func
if __name__ == "__main__":
    # public cloud service
    public_cloud_server(open_api_key_yaml=open_api_key_yaml,
                        public_port=public_port,
                        private_port=private_port)
