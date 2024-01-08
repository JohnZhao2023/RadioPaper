# Import required libraries
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
from rouge_score import rouge_scorer
import socket
import yaml
import time
import pandas as pd

# Read the configuration file
with open('public_cloud.yaml', 'r') as file:
    yaml_data = yaml.safe_load(file)

# Get parameters
open_api_key_yaml = yaml_data['properties']['openai_api_key']
public_port = yaml_data['properties']['public-server-port']
private_port = yaml_data['properties']['private-server-port']

# Cache settings
underlying_embeddings = OpenAIEmbeddings(openai_api_key=open_api_key_yaml)
store = LocalFileStore("./cache/")
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings, store, namespace=underlying_embeddings.model
)

# Read standard answers from the CSV file
standard_answers_df = pd.read_csv('/path/to/your/csv/file.csv')  # Replace with your CSV file path


# Function to send the unencrypted answer to the private cloud
def send_answer_to_private_cloud(encrypted_answer, private_cloud_host, private_cloud_port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((private_cloud_host, private_cloud_port))
        print(f"Connecting to the private cloud {private_cloud_host} succeeded!")
        s.sendall(encrypted_answer.encode('utf-8'))


# Function to calculate the ROUGE-1 score
def calculate_rouge_score(reference, hypothesis):
    scorer = rouge_scorer.RougeScorer(['rouge1'], use_stemmer=True)
    scores = scorer.score(reference, hypothesis)
    return scores['rouge1'].fmeasure


# Public cloud server function
def public_cloud_server(open_api_key_yaml, public_port=8000, private_port=8000, host='0.0.0.0'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, public_port))
        s.listen()
        print(f"Success! The {host} is listening on the port {public_port}...")

        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                data = conn.recv(1024*1024*16384).decode('utf-8')
                if not data or len(data) < 1:
                    continue

                index = data.find("__xxxxx__")
                if index == -1:
                    continue

                encrypted_question = data[:index]
                encrypted_markdown_content = data[index+9:]
                if len(encrypted_question) > 8192:
                    encrypted_question = encrypted_question[:8192]

                # Assuming you have decrypted the question and markdown content
                # decrypted_question = your_decryption_function(encrypted_question)
                # markdown_content = your_decryption_function(encrypted_markdown_content)

                # RAG process
                start_RAG_time = time.time()
                headers_to_split_on = [
                    ("#", "Header 1"),
                    ("##", "Header 2"),
                    ("###", "Header 3"),
                    ("####", "Header 4"),
                ]
                markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
                md_header_splits = markdown_splitter.split_text(markdown_content)

                retriever = FAISS.from_documents(md_header_splits, cached_embedder).as_retriever(search_kwargs={"k": 2})

                template = """How to use antctl command without bash character to implement question based only on the following context:
                {context}

                Question: {question}
                """
                prompt = ChatPromptTemplate.from_template(template)
                model = ChatOpenAI(model_name="gpt-4", openai_api_key=open_api_key_yaml)
                output_parser = StrOutputParser()
                setup_and_retrieval = RunnableParallel(
                    {"context": retriever, "question": RunnablePassthrough()}
                )

                chain = setup_and_retrieval | prompt | model | output_parser
                model_answer = chain.invoke(decrypted_question)

                # Calculate ROUGE-1 score
                standard_answer = standard_answers_df.loc[standard_answers_df['question'] == decrypted_question, 'answer'].iloc[0]
                rouge_score = calculate_rouge_score(standard_answer, model_answer)

                # Send the answer and ROUGE-1 score to the private cloud
                send_answer_to_private_cloud(f"Answer: {model_answer}\nROUGE-1 Score: {rouge_score}", addr[0], private_port)

                end_RAG_time = time.time()
                print(f"The time for RAG process is: {end_RAG_time - start_RAG_time} second")


if __name__ == "__main__":
    public_cloud_server(open_api_key_yaml=open_api_key_yaml, public_port=public_port, private_port=private_port)
