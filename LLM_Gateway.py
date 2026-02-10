# import yaml
import streamlit as st
from langchain_cohere import ChatCohere, CohereEmbeddings
# def fetch_api(path='api_key.yaml',key='api_key'):
#     with open(path, 'r') as file:
#         config = yaml.safe_load(file)
#     return config.get(key)

def nexa_ai(model="command-a-03-2025", temp=0,max=50):
    llm = ChatCohere(
        model=model,
        temperature=temp,
        cohere_api_key=st.secrets["COHERE_KEY"]
        max_tokens=max,
        )
    return llm

# from openai import OpenAI
# def nexa_ai():
#     client = OpenAI(
#         base_url="https://router.huggingface.co/v1",
#         api_key=fetch_api(key='hf_key'),
#     )

#     completion = client.chat.completions.create(
#         model="zai-org/GLM-4.7:novita",
#         messages=[
#             {
#                 "role": "user",
#                 "content": "What is the capital of France?"
#             }
#         ],
#     )

#     return completion.choices[0].message.content
# def embedding_model():
#     embeddings = CohereEmbeddings(
#     cohere_api_key=fetch_api(), model="embed-v4.0"
# )
#     return embeddings