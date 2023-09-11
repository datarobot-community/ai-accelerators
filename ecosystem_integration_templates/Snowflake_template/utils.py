#!/usr/bin/env python3
# -*- mode: python; python-indent-offset: 4 -*-

from IPython.display import display
import pandas as pd
import snowflake
from snowflake.connector.pandas_tools import write_pandas
import yaml

# we can skip the import snowfalke step entirely https://stephenallwright.com/python-connector-write-pandas-snowflake/
# this causes issues if they install snowflake connector and "snowflake" - https://stackoverflow.com/questions/74223900/snowflake-connector-python-package-not-recognized


def prepare_demo_tables_in_db(
    db_user=None,  # username to access snowflake database
    db_password=None,  # password
    account=None,  # Snowflake Account Identifier can be found in the db_url
    db=None,  # Database to Write_To
    warehouse=None,  # Warehouse
    schema=None,  # schema
):
    """description: method to prepare demo table in snowflake database
    reads from datasets.yaml

    by: gongoraj, demidov91 and jpgomes
        date: 12/22/2022
    """

    with snowflake.connector.connect(
        user=db_user,
        password=db_password,
        account=account,
        warehouse=warehouse,
        database=db,
        schema=schema,
    ) as con:
        with open("datasets.yaml") as f:
            config = yaml.safe_load(f)
            for key, value in config["datasets"].items():
                print("*" * 30)
                print("table:", value["table_name"])
                try:
                    df = pd.read_csv(value["url"], encoding="utf8")
                except:
                    df = pd.read_csv(value["url"], encoding="cp850")
                display(df.head())
                print("info for ", value["table_name"])
                print(df.info())
                print(
                    "writing", value["table_name"], "to snowflake from: ", value["url"]
                )
                write_pandas(
                    con, df, value["table_name"], auto_create_table=True, overwrite=True
                )
                con.commit()
