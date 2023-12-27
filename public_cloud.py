# import the lib with ChatGPT model and relevant libs
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import MarkdownHeaderTextSplitter
import socket


# check if the document is in the cache
def get_document_embeddings(document_embeddings_cache, documents):
    embeddings = []
    for doc in documents:
        if doc in document_embeddings_cache:
            # use embedding in cache
            embeddings.append(document_embeddings_cache[doc])
        else:
            # create new embedding
            embedding = OpenAIEmbeddings(openai_api_key="YOUR_OPENAI_API_KEY").embed(doc)
            document_embeddings_cache[doc] = embedding
            embeddings.append(embedding)

    return documents, embeddings


# the agent in charge of sending the undecrypted answer to the private cloud
def send_answer_to_private_cloud(encrypted_answer, private_cloud_host='xx.xx.xx.xx', private_cloud_port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # connect to the private cloud
        s.connect((private_cloud_host, private_cloud_port))

        # print the connection success info
        print(f"connecting to the private cloud {private_cloud_host} succeed!")

        # send the undecrypted answer
        s.sendall(encrypted_answer.encode('utf-8'))


# agent in charge of receiving the question and begin RAG process
def public_cloud_server(document_embeddings_cache, host='xx.xx.xx.xx', port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # bind the agent on the port to receive the question
        s.bind((host, port))
        s.listen()

        # print the info of the success of the listening to the port
        print(f"Success! The {host} is listening on the port {port}...")

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

                # if data:
                #     json_data = json.loads(data)
                #     encrypted_question = json_data['encrypted_question']
                #     encrypted_markdown_content = json_data['encrypted_markdown_content']
                #     print(encrypted_question)

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
                # encrypted_markdown_content, document_embeddings_cache = get_document_embeddings(document_embeddings_cache, encrypted_markdown_content)

                # start RAG process
                # data pre-processing
                headers_to_split_on = [
                    ("#", "Header 1"),
                    ("##", "Header 2"),
                    ("###", "Header 3"),
                    ("####", "Header 4"),
                ]
                markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
                # md_header_splits = markdown_splitter.split_text(encrypted_markdown_content[0].page_content)
                md_header_splits = markdown_splitter.split_text(encrypted_markdown_content)

                # retriever setting
                retriever = FAISS.from_documents(md_header_splits,
                                                 OpenAIEmbeddings(openai_api_key="YOUR_OPENAI_API_KEY")).as_retriever(search_kwargs={"k": 2})

                # model setting
                open_api_key = "YOUR_OPENAI_API_KEY"
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

                # send the encrypted answer to the private cloud
                if not encrypted_answer:
                    continue
                send_answer_to_private_cloud(encrypted_answer)

                # clean data
                data = []

            # print('Connection closed')


# main fun
if __name__ == "__main__":
    # define the cache
    document_embeddings_cache = {}

    # public cloud service
    public_cloud_server(document_embeddings_cache)
