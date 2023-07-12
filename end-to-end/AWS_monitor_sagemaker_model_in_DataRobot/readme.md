## Introduction 

This notebook walks you through the steps to train and host a SageMaker model that can be monitored in the DataRobot platform.

## Prerequisites

1. Terraform - Since this repo uses terraform to provision the AWS infrastructure, you to need to install terraform in your local environment. Read more about [how to install terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).
2. An AWS account.
3. A DataRobot account.
4. AWS CLI and Docker installed in your local environment.

## Build a DataRobot compatible SageMaker container to host and train models

In your local enviroment, go the directory `container`. Open the `Dockerfile` and inspect the Python libraries you need to install. Some of the popular python data science librairies are already installed, as well as libriaies that enable model monitoring in the DataRobot platform.

Once the Dockerfile is ready, run the following commands to build and push it to your AWS ECR repo.

    - aws ecr create-repository --repository-name "sagemaker-datarobot-decision-trees"

    - aws ecr get-login-password --region us-east-1|docker login --username AWS --password-stdin 012345678901.dkr.ecr.us-east-1.amazonaws.com/sagemaker-datarobot-decision-trees   (replace the region and account id with your own one)

    - docker build . -t sagemaker-datarobot-decision-trees

    - docker tag sagemaker-datarobot-decision-trees 123456789.dkr.ecr.us-east-1.amazonaws.com/sagemaker-datarobot-decision-trees:latest

    - docker push 012345678901.dkr.ecr.us-east-1.amazonaws.com/sagemaker-datarobot-decision-trees:latest (replace this with your own ECR repo url)


After some time, you should be able to see the image in your AWS ECR repo.

## Model building and hosting

Once the ECR image has been built, you can run the notebook `AWS_SageMaker_DataRobot_MLOps.ipynb` in your SageMaker notebook instance. 

Just upload the notebook together with the "data" directory to your SageMaker notebook instance and follow the instructions to run it.