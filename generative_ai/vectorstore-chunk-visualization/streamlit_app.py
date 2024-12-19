import datetime
import json
import os
import time
import warnings

from PIL import Image
import datarobot as dr
from datarobot.enums import (
    PromptType,
    VectorDatabaseChunkingMethod,
    VectorDatabaseEmbeddingModel,
)
from datarobot.models.genai.chat import Chat
from datarobot.models.genai.chat_prompt import ChatPrompt
from datarobot.models.genai.comparison_chat import ComparisonChat
from datarobot.models.genai.comparison_prompt import ComparisonPrompt
from datarobot.models.genai.custom_model_llm_validation import CustomModelLLMValidation
from datarobot.models.genai.llm import LLMDefinition
from datarobot.models.genai.llm_blueprint import LLMBlueprint, VectorDatabaseSettings
from datarobot.models.genai.playground import Playground
from datarobot.models.genai.vector_database import (
    ChunkingParameters,
    CustomModelVectorDatabaseValidation,
    VectorDatabase,
)
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain.chat_models import AzureChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_text_splitters import CharacterTextSplitter
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import streamlit as st
import tiktoken

warnings.filterwarnings("ignore")

# Azure API
OPENAI_DEPLOYMENT_NAME = "gpt-35-turbo-16k"
OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = "2024-02-15-preview"
OPENAI_MAX_TOKENS = 12000
OPENAI_API_BASE = json.loads(os.environ.get("MLOPS_RUNTIME_PARAM_OPENAI_API_BASE"))
OPENAI_API_KEY = json.loads(os.environ.get("MLOPS_RUNTIME_PARAM_OPENAI_API_KEY"))

# pca tsne components
pca_components = 10
tsne_components = 2

# kmeans cluster range
min_clusters = 2
max_clusters = 10

# JINA_EMBEDDING_T_EN_V1 is recommend for english, SUP_SIMCSE_JA_BASE is recommend for japanese
embedding_model = VectorDatabaseEmbeddingModel.SUP_SIMCSE_JA_BASE
chunking_method = VectorDatabaseChunkingMethod.RECURSIVE

# chunk parameters
chunk_size = 384
chunk_overlap_percentage = 50
separators = ["\n\n", "\n", " "]

# seed
seed = 42

# time sleep
time_sleep = 60


def split_text(text):
    tokenizer = tiktoken.get_encoding("cl100k_base")
    text = " ".join(text)
    tokens = tokenizer.encode(text)
    chunks = []
    startIndex = 0
    while startIndex < len(tokens):
        endIndex = startIndex + OPENAI_MAX_TOKENS
        chunks.append(tokens[startIndex:endIndex])
        startIndex = endIndex
    return [tokenizer.decode(chunk) for chunk in chunks]


def generate_summaries(texts):
    llm = AzureChatOpenAI(
        deployment_name=OPENAI_DEPLOYMENT_NAME,
        openai_api_type=OPENAI_API_TYPE,
        openai_api_base=OPENAI_API_BASE["payload"]["apiToken"],
        openai_api_version=OPENAI_API_VERSION,
        openai_api_key=OPENAI_API_KEY["payload"]["apiToken"],
        model_name=OPENAI_DEPLOYMENT_NAME,
        temperature=0,
        verbose=True,
    )

    # create the summarize prompt
    prompt_template: str = """この文章を要約してください : {question}"""  # if you use english, you can input [Please summarize the following text briefly]
    prompt = PromptTemplate.from_template(template=prompt_template)

    texts_list = split_text(texts)
    predictions = []
    for t in texts_list:
        prompt_formatted_str = prompt.format(question=t)
        prediction = llm.predict(prompt_formatted_str)
        predictions.append(prediction)
    predictions = " ".join(predictions)

    prompt_formatted_str = prompt.format(question=predictions)
    predictions = llm.predict(prompt_formatted_str)

    return predictions


def create_chunk_summary(df):
    chunk = df[["index", "text_chunks"]]
    chunk["Summary"] = chunk["text_chunks"].apply(lambda x: generate_summaries(x))
    return chunk


def create_cluster_summary(df, cluster_number):
    cluster = df.groupby(["label"])["index"].agg(list).reset_index()
    cluster["Chunk Count"] = cluster["index"].apply(lambda x: len(x))

    text_chunks = df.groupby(["label"])["text_chunks"].agg(list).reset_index()
    cluster = cluster.merge(text_chunks, on=["label"], how="left")

    cluster["Summary"] = cluster["text_chunks"].apply(lambda x: generate_summaries(x))
    return cluster


def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")


def create_vectordb(file):
    dr.Client(
        token=os.environ.get("DATAROBOT_API_TOKEN"),
        endpoint=os.environ.get("DATAROBOT_ENDPOINT"),
    )
    local_file_path = file
    use_case_name = file.split(".")[0]
    use_case = dr.UseCase.create(use_case_name)
    dataset = dr.Dataset.create_from_file(local_file_path)
    use_case.add(entity=dataset)

    chunking_parameters = ChunkingParameters(
        embedding_model=embedding_model,
        chunking_method=chunking_method,
        chunk_size=chunk_size,
        chunk_overlap_percentage=chunk_overlap_percentage,
        separators=separators,
    )
    vdb = VectorDatabase.create(dataset.id, chunking_parameters, use_case)

    time.sleep(time_sleep * 5)

    for n in range(5):
        time.sleep(time_sleep * n)
        try:
            vdb = VectorDatabase.get(vdb.id)
            vdb.download_text_and_embeddings_asset()
        except:
            continue
        else:
            break

    vdb_id = vdb.id
    df = pd.read_parquet(vdb_id + "_chunks_and_embeddings.parquet.gzip")

    return vdb_id, df


# ======================================== Start Streamlit ========================================#
st.title("Chunk Clustering In RAG")

# ======================================== image ========================================#
# image
dr_image = Image.open("dr.png")
st.image(dr_image)

# ======================================== tabs ========================================#
tab1, tab2, tab3, tab4 = st.tabs(
    ["VectorDB", "ClusterSummarize", "ChunkSummarize", "Visualization"]
)

with tab1:
    st.subheader("Upload Zip File!")
    uploaded_config = st.file_uploader("Zip File:")
    if uploaded_config is not None:
        file_name = uploaded_config.name
        with open(file_name, "wb") as file:
            file.write(uploaded_config.getvalue())

    def click_button():
        st.session_state.clicked = True

    if "clicked" not in st.session_state:
        st.session_state.clicked = False

    st.button("Run", on_click=click_button, key=1)

    if st.session_state.clicked:
        with st.status("Processing...", expanded=True) as status:
            start_time = time.time()

            st.write("Creating Vector Database...")

            for i in range(1):
                file_path = "vdb_chunk_" + str(max_clusters) + ".csv"
                if os.path.exists(file_path):
                    continue

                vdb_id, df = create_vectordb(file_name)
                end_time = time.time()
                st.write(
                    "Cumulative Execution Time: ", end_time - start_time, "seconds"
                )

                st.write("Creating Kmeans Cluster For Chunks...")
                for cluster_number in range(min_clusters, max_clusters + 1):
                    df_embedding = df.copy()
                    kmeans = KMeans(n_clusters=cluster_number, random_state=seed).fit(
                        list(df_embedding["embeddings"])
                    )
                    df_embedding["label"] = kmeans.labels_
                    df_embedding = df_embedding.reset_index()
                    pca = PCA(n_components=pca_components)
                    pca_result = pca.fit_transform(list(df_embedding["embeddings"]))
                    tsne = TSNE(
                        n_components=tsne_components,
                        random_state=seed,
                        init="pca",
                        learning_rate="auto",
                        perplexity=10,
                    )
                    tsne = tsne.fit_transform(pca_result)
                    df_embedding["tsne1"] = tsne[:, 0]
                    df_embedding["tsne0"] = tsne[:, 1]
                    df_embedding["index"] = df_embedding["index"] + 1
                    df_embedding["label"] = df_embedding["label"].astype("category")
                    df_embedding.to_csv(
                        "vdb_chunk_" + str(cluster_number) + ".csv", index=False
                    )

            end_time = time.time()
            st.write("Cumulative Execution Time: ", end_time - start_time, "seconds")

            status.update(label="Complete!", state="complete", expanded=False)

with tab2:

    def click_button2():
        st.session_state.clicked2 = True

    if "clicked2" not in st.session_state:
        st.session_state.clicked2 = False

    st.button("Run", on_click=click_button2, key=10)

    if st.session_state.clicked2:
        with st.status("Processing...", expanded=True) as status:
            start_time = time.time()
            st.write("Generating Summaries Of Clusters...")
            for cluster_number in range(min_clusters, max_clusters + 1):
                file_path = "cluster_summary_" + str(cluster_number) + ".csv"
                if os.path.exists(file_path):
                    continue
                st.write("Start Cluster:", cluster_number)
                df_cluster = pd.read_csv("vdb_chunk_" + str(cluster_number) + ".csv")
                cluster = create_cluster_summary(df_cluster, cluster_number)
                cluster.to_csv(
                    "cluster_summary_" + str(cluster_number) + ".csv", index=False
                )

            end_time = time.time()
            st.write("Cumulative Execution Time: ", end_time - start_time, "seconds")

            status.update(label="Complete!", state="complete", expanded=False)

with tab3:

    def click_button3():
        st.session_state.clicked3 = True

    if "clicked3" not in st.session_state:
        st.session_state.clicked3 = False

    st.button("Run", on_click=click_button3, key=100)

    if st.session_state.clicked3:
        with st.status("Processing...", expanded=True) as status:
            start_time = time.time()
            st.write("Generating Summaries Of Chunks...")
            for i in range(1):
                file_path = "chunk_summary.csv"
                if os.path.exists(file_path):
                    continue

                df_embedding = pd.read_csv("vdb_chunk_" + str(min_clusters) + ".csv")
                chunk = create_chunk_summary(df_embedding)
                chunk.to_csv("chunk_summary.csv", index=False)

            end_time = time.time()
            st.write("Cumulative Execution Time: ", end_time - start_time, "seconds")

            status.update(label="Complete!", state="complete", expanded=False)

with tab4:
    cluster_id = st.selectbox(
        "Select Cluster Number", range(min_clusters, max_clusters + 1), key=10000
    )

    if os.path.isfile("vdb_chunk_" + str(cluster_id) + ".csv"):
        df = pd.read_csv("vdb_chunk_" + str(cluster_id) + ".csv")
        df["label"] = df["label"].astype(str)
        fig = px.scatter(
            df, x="tsne0", y="tsne1", color="label", hover_data=["index"], text="index"
        )  # color="label",
        st.plotly_chart(fig, use_container_width=True)

    if os.path.isfile("chunk_summary.csv"):
        chunk_summary = pd.read_csv("chunk_summary.csv")
        chunk = df[["label", "index"]]
        chunk = chunk.sort_values(["label", "index"]).reset_index(drop=True)
        chunk = chunk.merge(chunk_summary, on=["index"], how="left")

        chunk.columns = ["Cluster Number", "Chunk Number", "Original Text", "Summary"]
        st.write("Chunk Summary")
        st.write(chunk)
        csv = convert_df(chunk)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="cluster" + str(cluster_id) + "_chunk_summary.csv",
            mime="text/csv",
        )

    if os.path.isfile("cluster_summary_" + str(cluster_id) + ".csv"):
        cluster_summary = pd.read_csv("cluster_summary_" + str(cluster_id) + ".csv")
        cluster_summary.columns = [
            "Cluster Number",
            "Chunk List",
            "Chunk Count",
            "Original Text",
            "Summary",
        ]
        st.write("Cluster Summary")
        st.write(cluster_summary)
        csv = convert_df(cluster_summary)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="cluster" + str(cluster_id) + "_summary.csv",
            mime="text/csv",
        )
