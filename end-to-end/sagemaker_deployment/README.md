# End to end ML workflow with a deployment in AWS SageMaker

<img src="images/DR%20and%20AWS%20Better%20Together.svg" width="250"/>
  
In this AI Accelerator notebook, you will build an AI/ML model within DataRobot which will then be deployed and hosted within AWS SageMaker. This will include uploading data for model training, model development, and exporting from DataRobot into SageMaker.  

Additionally, this notebook contains all the commands needed to prepare your AWS environment to successfully host a DataRobot model Scoring Code JAR file.  
  
These steps can also be done manually. You can view more documentation on how to do this [from the DataRobot documentation site](https://docs.datarobot.com/en/docs/platform/integrations/aws/sc-sagemaker.html#use-scoring-code-with-aws-sagemaker).

## Prerequisites

In order to successfully build up an environment in AWS to host a DataRobot model, you will need to have the following software installed on your system:
- Docker
- Access to Dockerhub
- DataRobot Python SDK (this notebook was tested with version 3.0.2)
- AWS Boto3 library

Additionally, you will need to have access to DataRobot with a generated API token and access to AWS with seperate generated access tokens.

## Scope

The notebook accomplishes the following tasks and builds the following items:

For AWS:

- ECR Repository
- S3 Bucket
- IAM Role for SageMaker
- SageMaker inference model
- SageMaker endpoint configuration
- SageMaker endpoint (for real time predictions)
- SageMaker batch transform job (for batch predictions)
  
For DataRobot:
- Create a project
- Build DataRobot models
- Create a Scoring Code JAR file from a DataRobot Model
  
## Directory outline

- *dr_model_sagemaker.ipynb*  
This is the python notebook that contains all the code needed to run the steps in this AI Accelerator.  
  
To make it easier to get up and running, the following folders include sample data that is used by the notebook for model training and for making predictions against.
- *scoring_data*  
This folder contains two datasets for making predictions against the model that has been deployed to AWS SageMaker. the 1 row dataset is for testing real time predictions while the 10k row dataset is for testing batch predictions.
- *training_data*  
This folder contains public sample data from Lending Club that will be used to train a simple binary classification model within DataRobot.

Author: Alex Yeager \
Version Date: 12/22/2022
