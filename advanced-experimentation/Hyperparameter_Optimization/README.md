# Hyperparameter Optimization in DataRobot

**HyperParm_Opt_Core_Concepts** reviews foundational concepts of how DataRobot defines and selects blueprints, the mechanics of tuning models from the API, and implements additional grid search approaches. 

**HyperParam_Opt_BayesianOptimization** builds on the core concepts and implements asynchronous Bayesian Optimization.

Together these notebooks provide:

- A better understanding of a DataRobot blueprint
- A better understanding of how to tune models in DataRobot via the Python client
- Helper functions to perform brute force tuning with parallel use of your modeling workers
- Helper functions to extract hyperparameters from all similar models, and tune both preprocessing and model hyperparameters

## Background: Hyperparameters in the context of a DataRobot experiment

In machine learning, hyperparameter tuning is the act of adjusting the "settings" (referred to as hyperparameters) in a machine learning algorithm, whether that's the learning rate for an XGBoost model or the activation function in a neural network. Many methods for doing this exist, with the simplest being a brute force search over every feasible combination. While this requires little effort, it's extremely time-consuming as each combination requires fitting the machine learning algorithm. To this end, practitioners strive to find more efficient ways to search for the best combination of hyperparameters to use in a given prediction problem. ataRobot employs a proprietary version of [pattern search](https://app.datarobot.com/docs/modeling/analyze-models/evaluate/adv-tuning.html#set-the-search-type) for optimization not only for the machine learning algorithm's specific hyperparameters, but also the *respective data preprocessing needed to fit the algorithm*, with the goal of quickly producing high-performance models tailored to your dataset. 

While the approach used at DataRobot is sufficient in most cases, you may want to build upon DataRobot's Autopilot modeling process by custom tuning methods. In this AI Accelerator, you will familiarize yourself with DataRobot's fine-tuning API calls to control DataRobot's pattern search approach as well as implement a modified brute-force gridsearch for the text and categorical data pipeline and hyperparametes of an XGBoost model. This notebook serves as an introductory learning example that other approaches can be built from.  Bayesian Optimiation, for example, leverages a probabilistic model to judiciously sift through the hyperparameter space to converge on an optimal solution, and will be presented next in this accelerator bundle.

Note that as a best practice, wait until the model is in a near-finished state before searching for the best hyperparameters to use. Ensure that the following have already been finalized:

- Training data (e.g., data sources)
- Model validation method (e.g., group cross-validation, random cross-validation, or backtesting. How the problem is framed influences all subsequent steps, as it changes error minimization.)
- Feature engineering (particularly, calculations driven by subject matter expertise)
- Preprocessing and data transformations (e.g., word or character tokenizers, PCA, embeddings, normalization, etc.)
- Algorithm type (e.g. GLM, tree-based, neural net)

These decisions typically have a larger impact on model performance compared to adjusting a machine learning algorithm's hyperparameters (especially when using DataRobot, as the hyperparameters chosen automatically are pretty competitive).  
