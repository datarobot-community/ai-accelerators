## DataRobot lineage viewer

This accelerator uses an application that allows you to view dependency graphs for DataRobot Use Cases. It is Use case-centric, so all assets for a use case are retrieved, and DataRobot fills in all of the asset parents.  

![lineage](./dr_lineage_app.gif)

## Run and use with node.js

```
node server.js
```

Go to `localhost:8000` to view the app.  You'll need to provide your API key and endpoint to retrieve and view your Use Cases.  

## Build, run, and use with Docker

```
docker build --platform="linux/amd64" -t lineage-app .
docker run --publish 8080:8080 lineage-app   
```

Go to `localhost:8080/apps` to view the app.  You'll need to provide your API key and endpoint to retrieve and view your Use Cases.

## Push to DataRobot

Once you've built the image, save it via the following command:

```
docker save -o lineage_app.tar lineage-app
```

Now use [`drapps`](https://github.com/datarobot/dr-apps) to push the application to DataRobot:

```
drapps create -i lineage-app.tar "DataRobot Lineage App"
```
