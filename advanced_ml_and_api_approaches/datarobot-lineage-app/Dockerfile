FROM node:latest
# WORKDIR /lineage
RUN apt-get update -y && apt-get install python3-pip nginx -y
RUN python3 -m pip config set global.break-system-packages true && python3 -m pip install datarobot python-dotenv
COPY . /lineage
COPY default.conf /etc/nginx/conf.d/default.conf
RUN chmod -R 777 /lineage
ENTRYPOINT nginx && node /lineage/server.js 