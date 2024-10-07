# Using Feature Discovery SQL in other Spark clusters

This guidebook offers an example of running Feature Discovery SQL in a Docker-based Spark cluster. It walks you through the process of setting up a Spark cluster in Docker, registering custom User Defined Functions (UDFs), and executing complex SQL queries for feature engineering across multiple datasets. The same approach can be applied to other Spark environments, such as GCP Dataproc, Amazon EMR, Cloudera CDP, ... providing flexibility for running Feature Discovery on various Spark platforms.

## Problem framing

More often than not, features are split across multiple data assets. Bringing these data assets together can take a lot of work—joining them and then running machine learning models on top. It's even more difficult when the datasets are of different granularities. In this case, you have to aggregate to join the data successfully.

Feature Discovery solves this problem by automating the procedure of joining and aggregating your datasets. After defining how the datasets need to be joined, you leave feature generation and modeling to DataRobot.

Feature Discovery uses Spark to perform joins and aggregations, generating Spark SQL at the end of the process. In some cases, you may want to run this Spark SQL in other Spark clusters to gain more flexibility and scalability for handling larger datasets, without the need to load data directly into the DataRobot environment. This approach allows you to leverage external Spark clusters for more resource-intensive tasks.

This notebook provides an example of running Feature Discovery SQL in docker-based Spark cluster. 

## Pre-requisites
- Docker installed
- Docker compose installed
- Download required datasets, UDFs jar and (optional) environment file

**Compatibility**
- The Feature Discovery SQL is compatible with Spark 3.2(.2) & Spark 3.4(.1) and Scala 2.12(.15). Using different Spark & Scala versions might lead to errors.
- UDFs jar and environment files can be obtained from (note that environment file is only required if working with Japanese text):
  - Spark 3.2.2
    - [UDFs](https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/feature_discovery/spark-udf-spark-3.2.2_scala-2.12.15_py37_linux-x86_64.jar)
    - [Environment file](https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/feature_discovery/venv_spark-3.2.2_scala-2.12.15_py37_linux-x86_64.tar.gz)
  - Spark 3.4.1
    - [UDFs](https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/feature_discovery/spark-udf-spark-3.4.1_scala-2.12.15_py37_linux-x86_64.jar)
    - [Environment file](https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/feature_discovery/venv-spark-udf-spark-3.4.1_scala-2.12.15_py37_linux-x86_64.tar.gz)
- Specific spark versions can be obtained from [https://archive.apache.org/dist/spark/](https://archive.apache.org/dist/spark/)

## Files overview
The file structure is organized as follows:
```bash
.
├── Using Feature Discovery SQL in other Spark clusters.ipynb
├── apps
│    ├── DataRobotRunSSSQL.py
│    ├── LC_FD_SQL.sql
│    ├── LC_profile.csv
│    ├── LC_train.csv
│    └── LC_transactions.csv
├── data
├── libs
│    ├── spark-udf-assembly-0.1.0.jar
│    └── venv.tar.gz
├── docker-compose.yml
├── Dockerfile
├── start-spark.sh
└── utils.py
```
- File `Using Feature Discovery SQL in other Spark clusters.ipynb`: This notebook provides a framework for running Feature Discovery SQL in a new Spark cluster on Docker.
- File `docker-compose.yml`, `Dockerfile`, `start-spark.sh` are files will be used by Docker to build and start Docker container with Spark.
- File `utils.py` includes helper function to download datasets & UDFs jar.
- Directory `app` includes:
  - Spark SQL (file with `.sql` extension)
  - Datasets (files with `.csv` extension)
  - Helper function (files with `.py` extension) to parse and execute the SQL
- Directory `libs` includes:
  - User Defined Functions (UDFs) jar file
  - Environment file (only required if datasets include Japanese text, which requires Mecab tokenizer to handle)
- Directory `data` is empty, will be used to store the output result
  
**\*Note that the datasets, UDFs jar & environment files are initially not available, they have to be downloaded in the next section.**

## Using the code

### Build the Docker image
```bash
docker build -t apache-spark:3.2.1 .
```
### Start the Spark cluster using docker-compose 
```bash
docker-compose up -d
```
### Open bash terminal on the Spark Master
```bash
docker exec -it spark-master bash
```
### Check UDFs registering
Open pyspark shell
```bash
/opt/spark/bin/pyspark \
--master spark://spark-master:7077 \
--jars /opt/spark-libs/spark-udf-assembly-0.1.0.jar \
-c spark.sql.caseSensitive=true
```
or if you need Mecab tokenizer to handle Japanese text
```bash
/opt/spark/bin/pyspark \
--master spark://spark-master:7077 \
--jars /opt/spark-libs/spark-udf-assembly-0.1.0.jar \
--archives=/opt/spark-libs/venv.tar.gz#environment \
-c spark.executor.extraJavaOptions="-Djava.library.path=./environment/lib" \
-c spark.executorEnv.VIRTUAL_ENV="./environment" \
-c spark.sql.caseSensitive=true
```
then run a simple pyspark command to view UDFs functions, you should have 20+ functions that start with `dr_` prefix.
```bash
spark._jvm.com.datarobot.safer.spark.extensions.SAFER(spark._jsparkSession).registerFunctions()
sql("SHOW FUNCTIONS LIKE 'dr*'").show(50,50)
exit()
```

### Submit Spark jobs using spark-submit
You can use the following command:
```bash
docker exec -it spark-master /opt/spark/bin/spark-submit \
  --conf "spark.sql.legacy.timeParserPolicy=LEGACY" \
  --master spark://spark-master:7077 \
  --jars /opt/spark-libs/spark-udf-assembly-0.1.0.jar \
  -c spark.sql.caseSensitive=true \
  /opt/spark-apps/DataRobotRunSSSQL.py \
    /opt/spark-apps/LC_FD_SQL.sql \
    --input=csv,primary_dataset=/opt/spark-apps/LC_train.csv \
    --input=csv,LC_profile=/opt/spark-apps/LC_profile.csv \
    --input=csv,LC_transactions=/opt/spark-apps/LC_transactions.csv \
    --output=csvfile,/opt/spark/spark-warehouse/result.csv  # output directory
```
Some things to be noted:
- The first input should be the primary dataset.
- Helper function `DataRobotRunSSSQL.py` is used to parse the SQL and execute them, see more details below.
- If you need Mecab tokenizer to handle Japanese text, you should use environment file in the command as mentioned in [link](#Check-UDFs-registering)
- The column order is no longer the same as the input file.

### Exit and cleanup
```bash
# exit spark master docker container
exit

# shutdown docker
docker-compose down

# remove apache-spark docker image
docker image rm apache-spark:3.2.1
```

## Appendix

### DataRobotRunSSSQL.py
#### Usage
This helper function is used to parse and execute Feature Discovery SQL. It takes the below arguments:
- `feature-discovery-recipe.sql`: DataRobot feature discovery recipe file downloaded from DataRobot.
- `--input=<input_type>,<table_name>[=source file location if it is not a table]`: the first input must be the primary dataset.
- `--input=<input_type>,<table_name>[=source file location if it is not a table]`: as many secondary datasets as required, the table name must match the table name in the relationships graph.
- `--output=<output_type>,<tablename or location>`
- `[--enableHiveSupport]` if the spark session requires hive support for tables.

#### Input datasets
- `csv` if the file is of type csv.
- `table` if it is being read from a table recognized by the spark session.
**Example**
- `--input=csv,my_table_name=/my/fully_qualified/path/to/my_file.csv` *data is being read from a file local to the spark master*
- `--input=csv,my_table_name=gs://my_bucket/and/the/path/to/my_file.csv` *data is being read from google bucket*
- `--input=csv,my_table_name` *the data is available to spark as a table*

#### Output dataset

- `csv` - this uses the spark csv writer, it will create a directory containing 1 or more csv files. The files will contain a header record.
- `parquet` - this uses the spark parquet writer, it will create a directory containing 1 or more parquet files.
- `table` - this will create a table of the provided with the physical path to the data as per the warehouse setting for spark
- `csvfile` - this will create a single csv file in the provide local file system location, **do not do use this** for anything other than testing of small datasets because the dataframe gets pulled to the sparkmaster during the toPandas function call and can very easily create out of memory issues.

**Example**

- `--output table,result` *creates a table called result in the default spark warehouse location*
- `--output csv,hdfs://users/me/some/folder/result` *creates a folder called result in the hdfs cluster which contains the output csv files*
- `--output csv,gs://my_bucket/and/the/path/to/result` *creates a folder called result in the bucket and location as defined*
- `--output parquet,gs://my_bucket/and/the/path/to/result` *creates a folder called result in the bucket and location as defined and will output the data as parquet.*


Author: Harry Dinh and John Edwards 
Version Date: 15/10/2024
