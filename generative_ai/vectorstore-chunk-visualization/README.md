# Vectorstore Chunk Visualization App With DataRobot

**Author:** senkin.zhan@datarobot.com

**Demo Data:** https://s3.us-east-1.amazonaws.com/datarobot_public_datasets/ai_accelerators/DORAEMON.zip

## Problem framing

This AI Accelerator demonstrates how to implement a Streamlit application to gain insight from vectordatabase of chunks, RAG developer can compare similarity between chunks and remove unnecessary data during RAG development.

## Accelerator overview

The following steps outline the accelerator workflow.If you have errors refresh browser and click button again always can solve network or azure api issues.

## From nextgen->registry->application, build a streamlit application.
![add_app_source](image/add_app_source.png)
![build_env](image/build_env.png)
![build_source](image/build_source.png)
![add_credential](image/add_credential.png) 
![runtime_parameters](image/runtime_parameters.png)

## If has exsited vectorstore, input vectorstore id.
![upload_document](image/exsited_vdb.png)

## If need to create a new vectorstore, upload document to build vectorstore on datarobot.
![upload_document](image/upload_document.png)

## Build summary of cluster by Azure OpenAI service.
![cluster_summary](image/cluster_summary.png)

## Build summary of chunk by Azure OpenAI service.
![chunk_summary](image/chunk_summary.png)

## Select how many clusters of chunk.
![cluster_number](image/cluster_number.png)

## View the summaries of cluster and chunk.
![cluster_summary_text](image/cluster_summary_text.png)
![chunk_summary_text](image/chunk_summary_text.png)


