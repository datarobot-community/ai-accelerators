# Create a vectorstore chunk visualization app with DataRobot

**Author:** senkin.zhan@datarobot.com

**Demo data:** https://s3.us-east-1.amazonaws.com/datarobot_public_datasets/ai_accelerators/godzillaMinusOne.zip

## Problem framing

This AI Accelerator demonstrates how to implement a Streamlit application to gain insights from a vector database of chunks. A RAG developer can compare similarity between chunks and remove unnecessary data during RAG development.

## Accelerator overview

The following steps outline the accelerator workflow. If you experience network or Azure API errors while running the Streamlit application, refresh the browser and run the application again.

1. In the DataRobot application, navigate to **NextGen > Registry > Applications**.
2. Build a Streamlit application.

![add_app_source](image/add_app_source.png)
![build_env](image/build_env.png)
![build_source](image/build_source.png)
![add_credential](image/add_credential.png) 
![runtime_parameters](image/runtime_parameters.png)

3. Upload the document to build a vectorstore with DataRobot.

![upload_document](image/upload_document.png)

4. Build a summary of clusters with Azure OpenAI services.
![cluster_summary](image/cluster_summary.png)

5. Build a summary of chunks with Azure OpenAI service.
![chunk_summary](image/chunk_summary.png)

6. Select how many clusters to chunk.
![cluster_number](image/cluster_number.png)

7. View the summaries of clusters and chunks for analysis.
![cluster_summary_text](image/cluster_summary_text.png)
![chunk_summary_text](image/chunk_summary_text.png)


