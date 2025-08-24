
import time
import streamlit as st
from langchain.prompts import ChatPromptTemplate
from langchain.vectorstores import FAISS
from langchain.storage import LocalFileStore
from langchain.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, CacheBackedEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.callbacks.base import BaseCallbackHandler

st.set_page_config(
    page_title="DocumentGPT",
    page_icon="📄",
)


    # *argument :on_llm_start(1,2,3,4) is okay
    # **kwargs means keyword argument on_llm_start(a=1,b=1, a=4) is okay


class ChatCallbackHandeler(BaseCallbackHandler):

    message = ""

    def on_llm_start(self, *args, **kwargs):
        self.message_box = st.empty()

    def on_llm_end(self, *args, **kwargs):
        save_message(self.message, "ai")

    def on_llm_new_token(self, token, *args, **kwargs):
        self.message += token
        self.message_box.markdown(self.message)

llm = ChatOpenAI(
    temperature=0.1,
    streaming=True,
    callbacks=[ChatCallbackHandeler()]
    )


@st.cache_data(show_spinner="Embedding file...")
def embed_file(file):
    file_content = file.read()
    file_path = f"./.cache/files/{file.name}"
    with open(file_path, "wb") as f:
        f.write(file_content)

    cache_dir = LocalFileStore(f"./.cache/embeddings/{file.name}")
    splitter = CharacterTextSplitter.from_tiktoken_encoder(
        separator="\n",
        chunk_size=600,
        chunk_overlap=100,
    )

    loader = UnstructuredFileLoader(file_path)

    docs = loader.load_and_split(text_splitter=splitter)
    embeddings = OpenAIEmbeddings()

    cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
        embeddings,
        cache_dir
    )


    vectorstore = FAISS.from_documents(
        documents=docs,
        embedding=cached_embeddings
    )

    retriever  =vectorstore.as_retriever()
    return retriever

def save_message(message, role):
    st.session_state["messages"].append({"message": message, "role": role})

def send_message(message, role, save=True):
    with st.chat_message(role):
        st.markdown(message)

    if save:
       save_message(message, role)


def paint_history():
    for message in st.session_state["messages"]:
        send_message(message["message"], message["role"], save=False)
        
def format_docs(docs):
    return "\n\n".join(document.page_content for document in docs)



prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Answer the question using ONLY the follwing context. If you don't know the answer just say you don't know. DONT' make anything up.
     
    Context:{context}
""" ),
    ("human", "{question}"),
])

st.title("DocumentGPT")

st.markdown("""
Welcome!\n
Use this chatbot to ask questions to an AI about your files!\n
Upload your file on the side bar            
""")

with st.sidebar:
    file = st.file_uploader("Upload a.txt .pdf or .docx file", type=["pdf", "txt", "docx"],)

if file:
    retriever = embed_file(file)
    send_message("I'm ready! Ask Away!", "AI", save=False)
    paint_history()
    message = st. chat_input("Ask anything about your file")
    if message:
        send_message(message, "human")

        chain ={
         # docs=retriever.invoke(message) manual 작업하고 동일
         # chain 입력으로 docs= "\n\n".join(document.page_content for document in docs) 이것도 해준.
         #   prompt = template.format_messages(context=docs, question=message) 이것도 파이프라인 prompt로 끝    
            "context" : retriever | RunnableLambda(format_docs),
            "question" : RunnablePassthrough()     
        } | prompt | llm

        with st.chat_message("ai"):
            chain.invoke(message)

else:
    st.session_state["messages"] = []
