# Create a demand forecasting What-If app

Author: Andrii Kruchko

Version Date: 02/28/2023

[DataRobot's API reference documentation](https://docs.datarobot.com/en/docs/api/reference/index.html)

This demand forecasting what-if app allows you to adjust certain known in advance (KA) variable values to see how changes in those factors might affect the forecasted demand.

Some examples of factors that might be adjusted include marketing promotions, pricing, seasonality, or competitor activity. By using the app to explore different scenarios and adjust KA inputs, you can make more accurate predictions about future demand and plan accordingly.

## App overview

The following steps outline how to run the app.

- Install the packages according to the configuration file `requirements.txt`: `pip install -r requirements.txt`

- Update the `config/config.toml` file with:
    - `API_KEY`: In DataRobot, navigate to **Developer Tools** by clicking on the user icon in the top-right corner. From here you can generate a API Key that you will use to authenticate to DataRobot. You can find more details on creating an API key [in the DataRobot documentation](https://app.datarobot.com/docs/api/api-quickstart/index.html#create-a-datarobot-api-key).
    - `ENDPOINT`: Determine your DataRobot API Endpoint. The API endpoint is the same as your DataRobot UI root. Replace {datarobot.example.com} with your deployment endpoint. API endpoint root: `https://{datarobot.example.com}/api/v2`. For users of the AI Cloud platform, the endpoint is `https://app.datarobot.com/api/v2`
    - `DATE_COL`: The datetime partition column defined before the project creation.
    - `SERIES_ID`: The multiseries ID column defined before the project creation.
    - `TARGET`: The target column defined before the project creation.
    - `KA_COLS`: A list of KA features.
    - `DEPLOYMENT_ID`: The deployment ID to use for making predictions. It can be created with [the previous accelerator](https://github.com/datarobot-community/ai-accelerators/tree/main/end-to-end/End_to_end_demand_forecasting). If you used the above accelerator to generate the deployment ID, you can use [this prediction file](https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/ts_demand_forecasting_scoring.csv) to test the app.
- Run the app with the command: `streamlit run demand_forecasting_app.py`.
- The Streamlit app should be available in your browser: http://localhost:8501.

## How to use the app

1. Upload the scoring dataset.
2. Update KA features or use the uploaded data as-is.
3. Run predictions.
4. Plot results: total, per group, or individual series.
5. Download predictions per scenario or all runs together.

![The app start page](app.png)
