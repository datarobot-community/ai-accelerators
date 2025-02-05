import logging
from typing import Dict

from backend.data_preparation import generate_and_execute_data_prep
from backend.data_quality_checks import run_data_quality_checks
import pandas as pd
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_all_data():
    """Clear all session state variables and cache"""
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    # Clear cache
    st.cache_data.clear()
    st.cache_resource.clear()


def get_dataset_metadata(df: pd.DataFrame) -> dict:
    """Generate metadata for a dataframe including summary stats and column info"""
    return {
        "summary_stats": df.describe(include="all").to_dict(),
        "columns": {
            col: {
                "dtype": str(df[col].dtype),
                "unique_count": df[col].nunique(),
                "sample_values": df[col].head().tolist(),
            }
            for col in df.columns
        },
        "shape": df.shape,
    }


@st.cache_data(show_spinner=False)
def cached_run_data_quality_checks(df: pd.DataFrame, metadata: Dict) -> Dict:
    """
    Cached wrapper for running data quality checks
    """
    return run_data_quality_checks(df, metadata["summary_stats"])


def display_data_quality_results(filename: str, df: pd.DataFrame):
    """Display data quality results with spinner"""
    st.markdown(f"##### Data Quality Analysis: {filename}")

    # Run the checks with a spinner
    with st.spinner("Running data quality checks..."):
        data_quality_results = cached_run_data_quality_checks(
            df, st.session_state["datasets_metadata"][filename]
        )

    logger.info("Proceeding to display results")

    # Display quality checks in separate expanders
    for i, (check, result) in enumerate(data_quality_results.items()):
        if result["issue_detected"]:
            display_name = check.replace("_", " ").title()
            is_first_issue = i == 0
            with st.expander(f"⚠️ {display_name}", expanded=is_first_issue):
                if "results_df" in result and not result["results_df"].empty:
                    st.dataframe(result["results_df"], hide_index=True, use_container_width=True)
                else:
                    st.markdown(result["recommendation"])


def main():
    st.set_page_config(
        page_title="AI Data Prep", page_icon="assets/datarobot_favicon.png", layout="wide"
    )

    # Add DataRobot logo
    st.image("assets/DataRobot_black.svg", width=300)

    # Initialize session state variables
    if "datasets" not in st.session_state:
        st.session_state["datasets"] = {}
    if "datasets_metadata" not in st.session_state:
        st.session_state["datasets_metadata"] = {}

    # Sidebar: CSV Upload and Clear Data
    st.sidebar.title("Upload CSV Files")
    uploaded_files = st.sidebar.file_uploader("Choose CSV files", accept_multiple_files=True)

    # Add Clear Data button to sidebar
    if st.sidebar.button("Clear All Data"):
        clear_all_data()
        st.rerun()

    if uploaded_files:
        for uploaded_file in uploaded_files:
            df = pd.read_csv(uploaded_file)
            st.session_state["datasets"][uploaded_file.name] = df
            # Store metadata for each dataset
            st.session_state["datasets_metadata"][uploaded_file.name] = get_dataset_metadata(df)

    # Add title
    st.title("AI Data Preparation Assistant")

    # Create tabs
    tab1, tab2 = st.tabs(["Data Quality Explorer", "AI Data Prep"])

    with tab1:
        # Data Quality Explorer Tab
        if not st.session_state.get("datasets"):
            st.info("Please upload CSV files in the sidebar.")
        else:
            for idx, (filename, df) in enumerate(st.session_state["datasets"].items()):
                # Dataset header
                st.subheader(f"Dataset: {filename}")

                # Data Preview expander
                with st.expander(f"📊 Data Preview", expanded=True):
                    st.dataframe(df.head(1000), height=550)

                # Summary Statistics expander
                with st.expander("Summary Statistics", expanded=False):
                    st.dataframe(df.describe(include="all"))

                # Display data quality results with spinner
                display_data_quality_results(filename, df)

                # Add separator between datasets
                st.markdown("---")

    with tab2:
        if not st.session_state.get("datasets"):
            st.info("Please upload CSV files in the sidebar.")
        else:
            st.subheader("Select Data Quality Issues to Resolve")
            selected_issues = {}
            for filename, df in st.session_state["datasets"].items():
                data_quality_results = cached_run_data_quality_checks(
                    df, st.session_state["datasets_metadata"][filename]
                )
                selected_issues[filename] = {}
                for check, result in data_quality_results.items():
                    if result["issue_detected"]:
                        if st.checkbox(f"{filename} - {check}"):
                            selected_issues[filename][check] = result

            st.subheader("Additional Data Preparation Steps")
            user_instructions = st.text_area("Enter additional data preparation instructions")

            if st.button("Generate and Execute Data Prep"):
                with st.spinner("Generating and executing data preparation code..."):
                    result = generate_and_execute_data_prep(
                        st.session_state["datasets_metadata"], selected_issues, user_instructions
                    )

                    if isinstance(result, list):
                        st.session_state["processed_dataframes"] = result

                        # Create a container for results
                        results_container = st.container()

                        with results_container:
                            # Display the generated code
                            st.subheader("Generated Data Preparation Code")
                            if "generated_code" in st.session_state:
                                st.code(
                                    st.session_state["generated_code"]["code"], language="python"
                                )

                            # Show success message
                            st.success("✅ Data preparation completed successfully!")

                            # Display processed datasets
                            st.subheader("Processed Datasets")
                            for i, df in enumerate(st.session_state["processed_dataframes"]):
                                with st.expander(f"Processed Dataset {i+1}", expanded=True):
                                    # Display first 1000 rows
                                    st.dataframe(df.head(1000), height=600)

                                    # Add download button
                                    csv = df.to_csv(index=False).encode("utf-8")
                                    st.download_button(
                                        label=f"Download Dataset {i+1} as CSV",
                                        data=csv,
                                        file_name=f"processed_dataset_{i+1}.csv",
                                        mime="text/csv",
                                    )
                    else:
                        failed_code, error_msg = result
                        st.error("❌ Data preparation failed after maximum attempts!")

                        # Display the failed code
                        st.subheader("Failed Code")
                        st.code(failed_code, language="python")

                        # Display the error message
                        st.error(f"Error Details:\n{error_msg}")

            # Show existing results if available
            elif st.session_state.get("processed_dataframes"):
                st.subheader("Processed Datasets")
                for i, df in enumerate(st.session_state["processed_dataframes"]):
                    with st.expander(f"Processed Dataset {i+1}", expanded=True):
                        st.dataframe(df.head(1000))
                        st.write("Shape:", df.shape)

                        # Add download button
                        csv = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label=f"Download Dataset {i+1} as CSV",
                            data=csv,
                            file_name=f"processed_dataset_{i+1}.csv",
                            mime="text/csv",
                        )


if __name__ == "__main__":
    main()
