# Master multiple datasets with Feature Discovery

This notebook provides a repeatable framework for end-to-end production ML with time-aware feature engineering across multiple tables, training dataset creation, model development, and production deployment.

### Problem framing

It is common to build training data from multiple sources, but this process can be time consuming and error prone, especially when you need to create many time-aware features.

- Event based data is present in every vertical. For example, customer transactions in retail or banking, medical visits, or production line data in manufacturing.
- Summarizing this information at the parent (Entity) level is necessary for most classification and regression use cases. For example, if you are predicting fraud, churn, or propensity to purchase something, you will likely want summary statistics of a customers transactions over a historical window.

This raises many practical considerations as a data scientist: How far back in time is relevant for training? Within that training period, which windows are appropriate for features? 30 days? 15? 7? Futher, which datasets and variables should you consider for feature engineering? Answering these conceptual questions requires domain expertise or interaction with business SMEs. 

In practice, especially at the MVP stage, it is common to limit the feature space you explore to what's been created previously or add a few new ideas from domain expertise.
- Feature stores can be helpful to quickly try features which were useful in a previous use case, but it is a strong assumption that previously generated lagged features will adapt well across all future use cases.
- There are almost always important interactions you haven't evaluated or thought of. 

Multiple tactical challenges arise as well. Some of the more commnon ones are:
- Time formats are inconsistent between datasets (e.g., minutes vs. days), and need to be handled correctly to avoid target leakage.
- Encoding text and categorical data aggregates over varying time horizons across tables is generally painful and prone to error.
- Creating a hardened data pipeline for production can take weeks depending on the complexity.
- A subtle wrinkle is that short and long-term effects of data matter, particularly with customers/patietnts/humans, and those effects change over time. It's hard to know apriori which lagged features to create.
- When data drifts and behavior changes, you very well may need entirely new features post-deployment, and the process starts all over.

All of these challenges inject risk into your MVP process. The best case scenario is historical features capture signal in your new use case, and further exploration to new datasets is limited when the model is "good enough".  The worst case scenario is you determine the use case isn't worth pursuing, as your features don't capture the new signal.  You often end up in the middle, struggling to know how to improve a model you are sure can be better. 

What if you could radically collapse the cycle time to explore and discover features across any relevant dataset?

This notebook provides a template to:

1. Load data into Snowflake and register with DataRobot's AI Catalog.
2. Configure and build time aware features across multiple historical time-windows and datasets using Snowflake (applicable to any database).
3. Build and evaluate multiple feature engineering approaches and algorithms for all data types.
4. Extract insights and identify the best feature engineering and modeling pipeline.
5. Test predictions locally.
6. Deploy the best performing model and all feature engineering in a Docker container, and expose a REST API.
7. Score from Snowflake and write predictions back to Snowflake.

For more information about the Python client, reference the [documentation](https://docs.datarobot.com/en/docs/api/api-quickstart/index.html).

### File overview

- **End-to-end Automared Feature Discovery Production Worfklow.ipynb**: This notebook provides a repeatable framework to build, customize, and deploy machine learning projects with data from multiple sources using time-aware feature engineeirng.    
- **utils.py**: Helper function to load data.    
- **requirements.txt**: Note: the `snowflake-connector-python` is required for this to run. Creating a virtual environment is recommended.         

Author: Joao Gomes and Chandler McCann.  
Version Date: 1/8/2023
