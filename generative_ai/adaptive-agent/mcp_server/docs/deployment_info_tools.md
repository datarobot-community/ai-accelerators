# Deployment Information Tools for Building Prediction Datasets

The Deployments MCP Server provides several tools to help AI agents understand deployment data requirements and build prediction datasets on the fly. These tools are essential for the use cases described in the tech spec where agents need to dynamically create prediction data.

## Tools Overview

### 1. `get_deployment_features`
**Purpose**: Get comprehensive information about the features required by a deployment.

**Returns**:
- Feature names and types (numeric, categorical, text, date)
- Feature importance scores (0-1 scale)
- Target information
- Time series configuration (if applicable)

**Example Use Case**: Agent needs to know what columns and data types are required to make predictions.

```json
{
  "deployment_id": "abc123",
  "model_type": "Regression",
  "target": "sales",
  "target_type": "Regression",
  "features": [
    {
      "feature_name": "temperature",
      "feature_type": "numeric",
      "importance": 0.85,
      "is_target": false
    },
    {
      "feature_name": "promotion",
      "feature_type": "categorical",
      "importance": 0.65,
      "is_target": false
    }
  ],
  "time_series_config": {
    "datetime_column": "date",
    "forecast_window_start": 1,
    "forecast_window_end": 7,
    "series_id_columns": ["store_id"]
  }
}
```

### 2. `get_deployment_training_data_sample`
**Purpose**: Get actual examples of training data to understand the expected format.

**Returns**: Sample CSV with metadata about the full dataset.

**Example Use Case**: Agent needs to see real examples of valid input data to understand formatting, value ranges, and patterns.

### 3. `generate_prediction_data_template`
**Purpose**: Generate a ready-to-use CSV template with proper structure.

**Returns**: CSV template with:
- All required columns in correct order
- Sample values appropriate for each feature type
- Metadata comments explaining the model

**Example Use Case**: Agent needs to quickly create a valid prediction dataset structure that can be filled with specific values.

### 4. `validate_prediction_data`
**Purpose**: Check if a dataset is valid for making predictions.

**Returns**: Validation report with:
- Errors (missing required features, wrong types)
- Warnings (missing low-importance features)
- Info (extra columns that will be ignored)

**Example Use Case**: Before making predictions, agent validates the generated data to ensure it will work.

## Example Agent Workflow

Here's how an agent might use these tools to handle a user request:

**User**: "I want to predict sales for next week for store_A with temperatures of 75°F each day and no promotions."

**Agent Workflow**:

1. **Get deployment features**:
   ```
   get_deployment_features(deployment_id="sales_forecast_deployment")
   ```
   → Learns it needs: date, temperature, promotion, store_id columns

2. **Generate template**:
   ```
   generate_prediction_data_template(deployment_id="sales_forecast_deployment", n_rows=7)
   ```
   → Gets CSV structure with 7 rows

3. **Modify template with user's values**:
   - Set temperature = 75 for all rows
   - Set promotion = 0 for all rows  
   - Set store_id = "store_A" for all rows
   - Set dates for next 7 days

4. **Validate the data**:
   ```
   validate_prediction_data(deployment_id="sales_forecast_deployment", file_path="prediction_data.csv")
   ```
   → Confirms data is valid

5. **Make predictions**:
   ```
   predict_realtime(deployment_id="sales_forecast_deployment", file_path="prediction_data.csv", forecast_point="2024-06-01")
   ```

## Benefits for AI Agents

1. **Self-documenting**: Agents can discover what data is needed without external documentation
2. **Type safety**: Feature type information prevents data type errors
3. **Validation**: Catch issues before attempting predictions
4. **Examples**: Training data samples show real-world valid inputs
5. **Templates**: Quick starting point for data generation

## Integration with LLMs

These tools are designed to provide information in formats that LLMs can easily understand and use:

- JSON responses for structured information
- CSV formats for tabular data
- Clear error messages for troubleshooting
- Metadata comments in generated templates

This enables agents to autonomously handle complex prediction scenarios without human intervention. 