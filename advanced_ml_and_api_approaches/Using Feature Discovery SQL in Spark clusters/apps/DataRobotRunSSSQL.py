import argparse
from collections import namedtuple
import os
import re
from typing import List, Union

import pandas as pd
from pyspark.sql import DataFrame, SparkSession


class CSVInputData:
    def __init__(self, table_name: str, csv_filename: str):
        self.type = "csv"
        self.table_name = table_name
        if "://" in csv_filename:
            # don't validate path if it is a url format, just assume it's ok
            self.absolute_file_path = csv_filename
        else:
            # since this is a local file lets test that it's there
            self.absolute_file_path = os.path.abspath(csv_filename)
            if not os.path.isfile(self.absolute_file_path):
                raise argparse.ArgumentTypeError(
                    f"The CSV file {self.absolute_file_path} does not exist"
                )

    def load_csv(self, spark: SparkSession):
        df = spark.read.csv(self.absolute_file_path, header=True, inferSchema=True)
        df.createOrReplaceTempView(self.table_name)
        print(f"\nLoaded CSV file {self.absolute_file_path} into table {self.table_name}")

    def validate_table(self, spark: SparkSession):
        try:
            result = spark.sql(f"SELECT * FROM {self.table_name}").count()
            print(f"\nTable {self.table_name} rows: {result}")
            result = spark.sql(f"DESCRIBE TABLE {self.table_name}").collect()
            print(f"\nTable {self.table_name} structure:")
            for row in result:
                print(f"  {row['col_name']}: {row['data_type']}")
            return True
        except Exception as e:
            print(f"\nError validating table {self.table_name}: {str(e)}")
            return False


class TableInputData:
    def __init__(self, table_name: str):
        self.type = "table"
        self.table_name = table_name

    def validate_table(self, spark: SparkSession):
        try:
            result = spark.sql(f"SELECT COUNT(*) FROM {self.table_name}").collect()
            print(f"\nTable {self.table_name} rows: {str(result)}")
            result = spark.sql(f"DESCRIBE TABLE {self.table_name}").collect()
            print(f"\nTable {self.table_name} structure:")
            for row in result:
                print(f"  {row['col_name']}: {row['data_type']}")
            return True
        except Exception as e:
            print(f"\nError validating table {self.table_name}: {str(e)}")
            return False


InputData = Union[CSVInputData, TableInputData]


class OutputData:
    def __init__(self, output_type: str, name: str):
        self.type = output_type
        if output_type == "csvfile":
            self.filename = name
        elif output_type in ["csv", "parquet"]:
            self.filespath = name
        elif output_type == "table":
            self.table_name = name
        else:
            raise ValueError("Output type must be either 'csv', 'parquet', 'csvfile' or 'table'")

    def save_output(self, spark: SparkSession, result: DataFrame):
        print(f"\nResult has {result.count()} records")
        if self.type == "csvfile":
            print(
                "WARNING - saving to local csv is not scalable and is only implemented for testing"
            )
            pandas_df = result.toPandas()
            pandas_df.to_csv(self.filename, index=False)
            print(f"\nSaved result to CSV file: {self.filename}")
        elif self.type == "table":
            result.write.saveAsTable(self.table_name, mode="overwrite")
            print(f"\nSaved result to table: {self.table_name}")
        elif self.type in "csv":
            result.write.mode("overwrite").format("csv").options(
                header=True, quote='"', escape='"', quoteAll=True
            ).save(self.filespath)
            print(f"\nSaved result to csv: {self.filespath}")
        elif self.type in "parquet":
            result.write.mode("overwrite").format("parquet").save(self.filespath)
            print(f"\nSaved result to parquet: {self.filespath}")


def validate_file(file_path: str) -> str:
    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        raise argparse.ArgumentTypeError(f"The file {abs_path} does not exist")
    return abs_path


def parse_input(input_str: str) -> InputData:
    parts = input_str.split(",", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            "Input must be in the format 'type,table_name[=csv_filename]'"
        )

    input_type = parts[0].lower()
    table_part = parts[1]

    if input_type == "csv":
        table_parts = table_part.split("=", 1)
        if len(table_parts) != 2:
            raise argparse.ArgumentTypeError(
                "CSV input must include filename: 'csv,table_name=csv_filename'"
            )
        return CSVInputData(table_parts[0], table_parts[1])
    elif input_type == "table":
        if "=" in table_part:
            raise argparse.ArgumentTypeError(
                "Table input should not include a filename: 'table,table_name'"
            )
        return TableInputData(table_part)
    else:
        raise argparse.ArgumentTypeError("Input type must be either 'csv' or 'table'")


def parse_output(output_str: str) -> OutputData:
    parts = output_str.split(",", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Output must be in the format 'type,name'")

    output_type = parts[0].lower()
    name = parts[1]

    if output_type not in ["csv", "table", "parquet", "csvfile"]:
        raise argparse.ArgumentTypeError(
            "Output type must be either 'csv', 'table', 'parquet', 'csvfile'"
        )

    return OutputData(output_type, name)


def build_DR_PRIMARY_TABLE(spark, table_name):
    query = (
        "CREATE OR REPLACE TEMPORARY VIEW `DR_PRIMARY_TABLE` AS \n"
        "SELECT \n"
        "* \n"
        f"FROM {table_name}"
    )
    result = spark.sql(query)
    result = spark.sql("select * from DR_PRIMARY_TABLE").count()
    print(f"\nTable DR_PRIMARY_TABLE rows: {str(result)}")
    result = spark.sql(f"DESCRIBE TABLE `DR_PRIMARY_TABLE`").collect()
    print(f"\nTable DR_PRIMARY_TABLE structure:")
    for row in result:
        print(f"  {row['col_name']}: {row['data_type']}")


def parse_sql_blocks(file_path: str) -> List[namedtuple]:
    # Define the named tuple
    SqlBlock = namedtuple("SqlBlock", ["block_description", "block_sql"])

    # Read the entire SQL file into a string
    with open(file_path, "r") as file:
        sql_content = file.read()

    # Split the content into blocks using the full BLOCK END comment
    blocks = re.split(r"/\*\s*BLOCK END -- .*?\*/", sql_content, flags=re.DOTALL)

    result = []
    for i, block in enumerate(
        blocks[:-1]
    ):  # Exclude the last split as it's after the last BLOCK END
        # Extract the block description (single line after "BLOCK START -- ")
        match = re.search(r"/\*\s*BLOCK START -- (.*?)(?:\n|\*\/)", block)
        if match:
            description = match.group(1).strip()
        else:
            description = f"Block {i+1}"

        # Remove the BLOCK START comment
        sql = re.sub(r"/\*\s*BLOCK START -- .*?\*/", "", block, flags=re.DOTALL)

        # Remove single-line comments
        sql = re.sub(r"/\*\s*-+\s*\*/", "", sql)  # Remove separator comments
        sql = re.sub(r"/\*\s*--.*?\*/", "", sql)  # Remove view name comments

        # Remove multi-line DESCRIPTION comments
        sql = re.sub(r"/\*\s*DESCRIPTION:.*?\*/", "", sql, flags=re.DOTALL)

        # Replace `dr_row_idx` with monotonically_increasing_id() in ORDER BY clause
        sql = re.sub(
            r"(ORDER BY\s*\n*\s*)`dr_row_idx`",
            r"\1monotonically_increasing_id()",
            sql,
            flags=re.IGNORECASE,
        )

        # Remove empty lines and strip whitespace
        sql = "\n".join(line.strip() for line in sql.split("\n") if line.strip())

        # Add to result
        result.append(SqlBlock(description, sql))

    # Handle the last block separately if it's not empty
    last_block = blocks[-1].strip()
    if last_block:
        # Remove single-line comments
        last_sql = re.sub(r"/\*\s*-+\s*\*/", "", last_block)  # Remove separator comments
        last_sql = re.sub(r"/\*\s*--.*?\*/", "", last_sql)  # Remove view name comments

        # Remove multi-line DESCRIPTION comments
        last_sql = re.sub(r"/\*\s*DESCRIPTION:.*?\*/", "", last_sql, flags=re.DOTALL)

        # Remove empty lines and strip whitespace
        last_sql = "\n".join(line.strip() for line in last_sql.split("\n") if line.strip())
        result.append(SqlBlock("Final Block", last_sql))

    return result


def main():
    parser = argparse.ArgumentParser(
        prog="DataRobotRunSSSQL", description="DataRobot Run Spark SAFER SQL"
    )
    parser.add_argument("sql", type=validate_file, help="SQL file (must exist)")
    parser.add_argument(
        "--input",
        type=parse_input,
        action="append",
        required=True,
        help="Input in the format 'type,table_name[=csv_filename]' (can be specified multiple times), the first entry is the master table",
    )
    parser.add_argument(
        "--output",
        type=parse_output,
        required=True,
        help="Output in the format 'type,name' where type is 'csv', 'parquet', 'table' or 'csvfile'",
    )
    parser.add_argument(
        "--enableHiveSupport",
        action="store_true",
        default=False,
        help="enable hive support in the spark context",
    )

    args = parser.parse_args()

    # Initialize Spark session
    ssb = SparkSession.builder.appName("SQLProcessor")
    if args.enableHiveSupport:
        ssb = ssb.enableHiveSupport()
    spark = ssb.getOrCreate()

    # Register and list DataRobot spark functions
    spark._jvm.com.datarobot.safer.spark.extensions.SAFER(spark._jsparkSession).registerFunctions()
    result = spark.sql("SHOW FUNCTIONS LIKE 'dr*'").collect()
    print(f"\nSpark DataRobot SAFER functions:")
    for row in result:
        print(f"  {row['function']}")

    # Process the arguments
    sql_file = args.sql  # Already absolute from validate_file
    inputs: List[InputData] = args.input
    output: OutputData = args.output

    # Process inputs
    for input_data in inputs:
        if isinstance(input_data, CSVInputData):
            input_data.load_csv(spark)
        input_data.validate_table(spark)

    # Build the DR_PRIMARY_TABLE
    build_DR_PRIMARY_TABLE(spark, inputs[0].table_name)

    # Execute the blocks of sql
    sql_blocks = parse_sql_blocks(sql_file)
    for block in sql_blocks:
        print(f"\nRunning SQL Block: {block.block_description}")
        result = spark.sql(block.block_sql)

    # Save result
    output.save_output(spark, result)

    # Clean up
    spark.stop()


if __name__ == "__main__":
    main()
