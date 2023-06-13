# Create a trading volume profile curve with a time series model factory

## Overview

In securities trading, it’s often useful to have an idea of how trading volume for a particular instrument will be distributed over the market session.  This is done by building a volume curve — essentially, a prediction of how much of the volume will fall within the different time intervals (“time slices”) in a trading day. Volume curves allow traders to better anticipate how to time and pace their orders and are used as inputs into algorithmic execution strategies such as VWAP (volume weighted average price) and IS (implementation shortfall).  

Historically, volume curves have been built by taking the average share of volume for a particular time slice over the last N trading days (for instance, the share of the daily volume in AAPL that traded between 10:35 and 10:40am on each of the last 20 trading days, on average), with manual adjustments to take account of scheduled events and anticipated differences.  Machine learning allows you to do this in a structured, systematic way.

The goal of this AI accelerator is to provide a framwork to build models that will allow you to predict how much of the next day trading volume will happen at each time interval. The granularity can vary from minute by minute (or even lower) to hourly or daily. If you are working with high granularity, such as minute by minute intervals, having a single time series model to predict the next 1440 minutes (or 480, based on how long the market is open) becomes problematic. 

Instead, consider a Time Series model per interval (minute, half hour, hour, etc.) so that each model is only forecasting one step ahead. You can then bring together the predictions of all the models to create the full curve for the next day. Furthermore, while a model is built to predict each time interval, the model isn't restricted to data for that interval, but can leverage a wider window.

While the motivation for this repository is a financial markets use case, it should be useful in other scenarios where predictions are required at a high resolution, such as predictive maintenance.

### Challenges

* The number of models or deployments can explode, and you need to keep track of all of them.
* Each model needs slightly different data.
* Even if you are creating a model per minute, you want to use data from earlier and later on in the day.
* You want to see a unified result (a single curve for the whole trading day).

### Approach

* Use a dataframe to track the project, model, or deployment corresponding to each minute.
* There is a data processing functionality that aggregates the raw data to the desired granularity while also incorporating "look behind" and "look ahead" features.
* Get predictions from all the projects and stitch them together to get the full picture.

### Workflow

This repository consists of 4 notebooks and a helper file. The notebooks are meant to be used in this order:

* `VolumeProfile_starter_code` - Build all the models required to produce a full "next day curve" of predictions. The final output is a controller file that collects all the projects builds and summarises different metrics.
* `RequestPredictions_leaderboard (optional)` - Obtain predictions from models created in the previous step to generate the "next day curve".
* `Create_Deployments` - Take in the controller file from the first notebook, deploy the top models in each project, and add a "deployment" column to the controller.
* `RequestPredictions_deployments` - Obtain predictions from the models that have been deployed for a more robust and "production ready" approach than using the Leaderboard.

## Example

To quickly test the approach proposed in this repository, DataRobot used ticker data for 10 symbols ('AAPL', 'AMZN', 'DIS', 'F', 'FB', 'NFLX', 'QQQ', 'SPY', 'VZ','WMT'), looking at minute by minute trading volumes between April 16 2018 and June 7th 2018. The data is stored in AWS, so the notebooks can be ran without modifications (the user must provide their credentials though). After creating the necessary models and deployments by running `VolumeProfile_starter_code` and `Create_Deployments`, DataRobot makes predictions for the last half hour of trading on June 8th and compares them to the actuals (this is all done in `RequestPredictions_deployments`. Examine the results of this comparison below.

![image](output.png)



