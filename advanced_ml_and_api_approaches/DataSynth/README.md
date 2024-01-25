# README

## 1. To Build Local Image

```shell
docker image rm datarobot_app_datasynth
docker build -t datarobot_app_datasynth .
```

## 2. To Test and Run Local Image

Run command
```shell
docker run \
    --env DATAROBOT_ENDPOINT="https://app.datarobot.com/api/v2" \
    --publish 8501:80 \
    --rm \
    datarobot_app_datasynth
```
Open the app and test it
http://localhost:8501


## 3. To Save Image when all is ok

```shell
rm -f ../datarobot_app_datasynth.tar.gz
docker save datarobot_app_datasynth | gzip > ../datarobot_app_datasynth.tar.gz
```


## 4. To Create the App in DataRobot

1. Goto the DataRobot Applications Page (https://app.datarobot.com/applications)
2. Click on "Use Template" on "Custom" under the "Create and App Using Custom Templates" Section of the page.
3. We are deploying the app using the method from "Option 2" and have already completed all the above so just click on the "Start" button
4. Select a name for your app, "DataRobot DataSynth" is appropriate for this app.
5. Choose the datarobot_app_datasynth.tar.gz file created in the "Save Image" step.
6. After the upload completes, click "Create" and then after a few minutes the app will be ready for use.

