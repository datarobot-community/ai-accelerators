## Project Deployment

Run the following shell commands to deploy the project:

```shell
dr task run infra:up-yes
```

In case the deployment process fails, you can try deleting it by running the following command:

```shell
dr task run infra:down-yes
```