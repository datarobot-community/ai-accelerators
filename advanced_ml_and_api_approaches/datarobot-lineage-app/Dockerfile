FROM nginxinc/nginx-unprivileged:latest
user root
RUN apt-get update -y && apt-get install python3-pip nodejs -y
RUN python3 -m pip config set global.break-system-packages true && python3 -m pip install datarobot python-dotenv
COPY . /lineage
RUN chmod -R 777 /lineage
COPY default.conf /etc/nginx/conf.d/default.conf
USER nginx
ENTRYPOINT nginx && cd /lineage &&  node server.js 
