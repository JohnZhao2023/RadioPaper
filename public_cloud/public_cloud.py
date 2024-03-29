# Import required libraries
import openai
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
openai.api_key = open_api_key_yaml

# Read standard answers from the CSV file
standard_answers_df = pd.read_csv('./antrea_questions_answers_updated.csv')


# Function to send the unencrypted answer to the private cloud
def send_answer_to_private_cloud(encrypted_answer,
                                 private_cloud_host,
                                 private_cloud_port=8000):
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
def public_cloud_server(public_port=8000, private_port=8000, host='0.0.0.0'):
    # socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # listen to the port to receive the msg from the private cloud
        s.bind((host, public_port))
        s.listen()
        print(f"Success! The {host} is listening on the port {public_port}...")
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                # receive the data
                data = conn.recv(1024*1024*16384).decode('utf-8')
                if not data or len(data) < 1:
                    continue

                index = data.find("__xxxxx__")
                if index == -1:
                    continue

                # get the question and context
                encrypted_question = data[:index]
                context = data[index+9:]
                if len(encrypted_question) > 8192:
                    encrypted_question = encrypted_question[:8192]

                # RAG process
                start_RAG_time = time.time()

                # setting the template
                template = f"""How to use antctl command without bash character to implement question mainly based on the following context:
                {context}

                Question: {encrypted_question}
                If there is no relevant information in the provided context, try to answer yourself,
                but tell user that you did not have any relevant context to base your answer on.
                Be concise and output the answer of size less than 500 tokens.
                """

                # get the answer from the model
                model_answer = openai.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": template,
                        }
                    ],
                    model="gpt-4"
                )
                model_answer = model_answer.choices[0].message.content

                # Calculate ROUGE-1 score
                # check if the question in the text data
                matching_rows = standard_answers_df.loc[standard_answers_df['Question'] == encrypted_question]

                if not matching_rows.empty:
                    # if in the text data then calculate the rouge_score
                    standard_answer = standard_answers_df.loc[standard_answers_df['Question'] == encrypted_question, 'Answer'].iloc[0]
                    rouge_score = calculate_rouge_score(standard_answer, model_answer)
                else:
                    # otherwise skip
                    print("No matching question found. Skipping...")
                    rouge_score = -1

                # print
                print(f"{model_answer}ROUGE-1 Score:{rouge_score}")

                # Send the answer and ROUGE-1 score to the private cloud
                send_answer_to_private_cloud(f"{model_answer}ROUGE-1 Score:{rouge_score}", addr[0], private_port)

                end_RAG_time = time.time()
                print(f"The time for RAG process is: {end_RAG_time - start_RAG_time} second")


if __name__ == "__main__":
    public_cloud_server(public_port=public_port, private_port=private_port)
