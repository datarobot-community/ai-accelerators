# AI data preparation assistant

**Author:** Brett Olmstead  
**Date created:** January 30th, 2025

## Introduction

The AI data preparation assistant is a powerful tool designed to streamline and automate the data preparation process. It combines automated data quality checks with AI-powered data preparation suggestions to help data scientists and analysts prepare their datasets more efficiently.

### Problem statement

Data preparation typically consumes 60-80% of a data scientist's time. This involves repetitive tasks like identifying quality issues, cleaning data, and transforming it into a suitable format for analysis. Manual data preparation is not only time-consuming, but prone to inconsistencies and human error.

### Solution

This application provides:

1. An automated data quality assessment across 12 key dimensions.
2. AI-powered suggestions for data preparation steps.
3. Automated code generation and execution for data cleaning.
4. Interactive visualizations of data quality issues.
5. A real-time data transformation preview.


## Features

### Data quality checks
- Missing value analysis
- Duplicate detection
- Date consistency verification
- Column name validation
- String value analysis
- Special character detection
- Data type optimization
- Outlier detection
- Statistical quality assessment
- Inlier pattern detection
- Format consistency checking
- Text variation analysis

### AI-powered data preparation
- Automated code generation for data cleaning
- Custom instruction support
- Real-time code execution implementing cleansing steps
- A preview of transformed datasets
- Downloadable results

## How to use the app

1. **Upload data**
   - Use the sidebar to upload one or more CSV files.
   - Preview uploaded data in the Data Quality Explorer tab.

2. **Explore data quality**
   - View automated quality check results.
   - Examine detailed statistics and visualizations.
   - Review suggested improvements.

3. **Generate data preparation code**
   - Select specific quality issues to address.
   - Add custom preparation instructions.
   - Generate and execute preparation code.

4. **Download transformed datasets**
   - Review the data preparation code.
   - Review the transformed dataset(s).
   - Download transformed dataset(s).

## Setup ⚙️

### Prerequisites
- Python 3.8 or higher
- DataRobot API access
- OpenAI API access

### Installation

1. **Clone the repository:**
    ```bash
    git clone [repository-url]
    cd [repository-name]
    ```

2. **Install required packages:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Deploy the Azure OpenAI model from DataRobot's Playground:**
    - Create a new Use Case or navigate to an existing one.
    - From the Playground, deploy an LLM Blueprint based on an Azure Open AI model such as Open AI GPT-4o.
    - Once deployed, navigate to the Console and record the deployment ID.
    - Alternatively, you can use an existing Open AI-based deployment by getting its deployment ID from the Console. It can be something deployed from the playground or a custom deployment. However, it must be Open AI-based deployment as this application relies on Open AI's structured outputs feature.

4. **Set up environment variables:**
    - Create a `.env` file in the root directory with the following template:
  
    ```env
    DATAROBOT_API_TOKEN=your_token_here
    DATAROBOT_ENDPOINT=your_endpoint_here
    CHAT_AGENT_DEPLOYMENT_ID=your_deployment_id_here # this is the deployment id from step 3
    ```

5. **Run the application locally for testing if needed:**
    
    ```bash
    streamlit run streamlit_app.py
    ```

6. **Deploy as a DataRobot custom application:**
    - In DataRobot, navigate to **Registry > Applications**.
    - From **Applications**, click **Add new application source**.
    - Follow the onscreen workflow to upload the files by dragging and dropping the contents of your cloned repo into the **Files** section.
    - Click **Build Application**.

## Technical architecture

The application is built using:
- **Streamlit**: A front-end interface with interactive components
- **Pandas**: Data manipulation and analysis
- **DataRobot**: AI model deployment and inference, application deployment platform
- **OpenAI**: Code generation and natural language processing
- **SciPy/NumPy**: Statistical analysis and computations
- **scikit-learn**: Machine learning and data preprocessing
- **statsmodels**: Statistical computations and testing


## Screenshots 📸

### 1: Upload files
Upload one or more CSV files using the sidebar uploader:
![Step 1 - Upload Files](Step%201%20-%20Upload%201%20or%20more%20files.png)

### 2: Data preview and quality checks
Review your data while the quality checks process:
![Step 2 - Data Preview](Step%202%20-%20Review%20a%20sample%20of%20the%20data%20while%20checks%20process.png)

### 3: Review quality issues
Review the detected data quality issues:
![Step 3 - Quality Issues](Step%203%20-%20Review%20the%20detected%20quality%20issues.png)

### Step 4: Select fixes
Choose which quality issues to address:
![Step 4 - Select Fixes](Step%204%20-%20Decided%20which%20fixes%20to%20implement.png)

### Step 5: Review and download
Review the generated code and download the transformed data:
![Step 5 - Review and Download](Step%205%20-%20Optionally%20review%20the%20generated%20code%20and%20download%20data.png)

## Contributions

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Acknowledgments

- DataRobot for providing the AI infrastructure.
- Streamlit for the interactive web framework.
- The open-source community for various supporting libraries.