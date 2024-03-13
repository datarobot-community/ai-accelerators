## Advanced Machine Learning and API Approaches
The DataRobot API's flexibility enables our data scientists, engineers and customers to build creative tools, quickly.  Notebooks in this repo are a grab-bag of topics that flex the use of the DataRobot API in different ways, and typically apply across install types and cloud providers. 

To incorpoarte into your workflow in your specific infrastructure, combine these with templates in the [ecosystem_integration_templates](https://github.com/datarobot-community/ai-accelerators/tree/main/ecosystem_integration_templates) folder. If something doesn't work or you have a suggestion, please open a [GitHub issue](https://github.com/datarobot-community/ai-accelerators/issues)  

## 💥 What's in here?
| Title | Primary Label | What it's good for | Other Labels| Extensibility to other Integrations |
|---|---|---|---|---|
| [Hyperparameter Optimization](https://github.com/datarobot-community/ai-accelerators/tree/main/advanced_ml_and_api_approaches/Hyperparameter_Optimization) | Parameter tuning | Learn how to use the API for hyperparameter tuning | - | High, advanced use of DataRobot API |
| [MLFLow with DataRobot experiments](https://github.com/datarobot-community/ai-accelerators/tree/main/advanced_ml_and_api_approaches/MLFLOW_w_datarobot_experiments) | MLFlow | Repeatable experiments that use MLflow to track key metrics across experiments e.g. model factories with multiple project settings, feature derivation windows | Parameter tuning, Model Factory | High |
| [Streamlit_template_datarobot_insights](https://github.com/datarobot-community/ai-accelerators/tree/main/advanced_ml_and_api_approaches/Streamlit_template_datarobot_insights) | Streamlit | Streamlit prediction insights app that can be easily customized, helps transform prediction explanations | Predictions | High, Streamlit baseline template |
| [Creating Custom Blueprints](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/creating_custom_blueprints/create_custom_blueprint.ipynb)| ComposableML | Learn how to create custom blueprint with ComposableML  | AutoML | High, advanced use of DataRobot API |
| [Custom Leaderboard Metrics](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/custom_leaderboard_metrics/custom_metrics.ipynb) | Model Evaluation | Learn how to rank models with custom metrics | - | High, advanced use of DataRobot API |
| [Customizing Lift Charts](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/customizing_lift_charts/customizing_lift_charts.ipynb)| Model Evaluation | Learn how to create a custom lift chart | - | High, advanced use of DataRobot API |
| [Data_enrichment_gcp_nlp_api](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/data_enrichment_gcp_nlp_api/GCP_enrich_sentiment.ipynb)| GCP | Enriching training data with GCP APIs for NLP (sentiment, etc). Extensible workflow to add new features for text, but extends to the Vision API, etc | Data Enrichment | High, could apply to Azure/ AWS, other GCP APIs |
| [Data_enrichment_ready_signal_ts](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/data_enrichment_ready_signal_ts/DataRobot_RXA.ipynb)|	Time series |Repeatable workflow to add external data such as weather, economic conditions, census data, etc, which can provide lift to time-series forecasts | Data Enrichment | High |
| [Feature Reduction with FIRE](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/feature_reduction_with_fire/feature_reduction_with_fire.ipynb) | Feature Reduction| Learn how to use Feature Importance Rank Ensembling for feature selection | - | High, advanced use of DataRobot API |
| [Fine_tuning_with_eureqa](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/fine_tuning_with_eureqa/fine_tuning_with_eureqa.ipynb)| Parameter tuning | Learn how to fine tune Eureqa genetic algorithm blueprints via the API | - | High, advanced use of DataRobot API |
| [Image dataprep pipeline in Databricks](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/image_dataprep_classification_databricks/Image%20Data%20Preparation.ipynb) | Databricks | Base64 conversion for images, project creation, and scoring pipeline | VisualAI | High, broadly applicable to computer vision |
| [Model Factory with Python Multithreading](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/model-factory-with-python-native-multithreading/Model%20Factory%20with%20Python%20Multithreading.ipynb)| Model Factory | Multithreading code to run projects in parallel with ~3x time reduction | - | High, python native libraries only|
| [Model migration across DataRobot instances](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/model_migration_across_dr_instances/Model_Migration_Example.ipynb)| ML Ops| Sample code to move a model between clusters | - | High, advanced use of DataRobot API |
| [Multi-model Analysis](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/multi_model_analysis/Multi-Model%20Analysis.ipynb) | Model Evaluation | Easily compare insights from models across different projects. Feature impact, model error, and partial dependence from models across N projects, for easy comparison. Inspired from our internal churn models | - | High, DR / Matplotlib/Seaborn focused |
| [Parameter_tuning_with_hyperopt](https://github.com/datarobot-community/ai-accelerators/blob/main/advanced_ml_and_api_approaches/parameter_tuning_with_hyperopt/Hyperparameter%20tuning%20with%20hyperopt.ipynb) | Parameter tuning | Code and workflow for Bayesian tuning with hyperopt package | - | High, applicable to nearly all blueprints |









