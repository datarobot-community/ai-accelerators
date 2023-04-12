#!/bin/sh

image=$1

docker run -v $(pwd)/test_dir:/opt/ml -p 8080:8080 \
-e AWS_ACCESS_KEY_ID="..." \
-e AWS_SECRET_ACCESS_KEY="..." \
-e AWS_DEFAULT_REGION="..." \
-e MLOPS_DEPLOYMENT_ID=" ... " \
-e MLOPS_MODEL_ID=" ... " \
-e MLOPS_SQS_QUEUE="https://sqs.us-east-1.amazonaws.com/..." \
-e prediction_type="Multiclass" \
-e CLASS_NAMES='["setosa", "versicolor", "virginica"]' \
--rm ${image} serve
