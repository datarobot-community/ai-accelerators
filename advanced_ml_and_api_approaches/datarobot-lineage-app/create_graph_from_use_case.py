import argparse
import copy
import itertools
import os
from pathlib import Path
import pprint

import datarobot as dr
from dotenv import load_dotenv

load_dotenv(override=True)
script_path = Path(__file__).parent.absolute()
print(script_path)

URL = "https://app.datarobot.com"

parser = argparse.ArgumentParser(
    description=__doc__,
    usage="python %(prog)s <input-file.{csv or json}> <output-file.{csv or json}>",
)
parser.add_argument(
    "--use-case-id",
    help="ID of use case for which you would like a graph",
)
parser.add_argument("--node-output-file", help="json output of nodes", default="dr_nodes.json")
parser.add_argument("--edge-output-file", help="json output of edges", default="dr_edges.json")

client = dr.Client()


def get_datastore_node(datastore_id, use_case_id):
    try:
        resp = client.get(f"externalDataStores/{datastore_id}").json()
        node = dict(
            assetId=datastore_id,
            label="datastore",
            name=resp["canonicalName"],
            driverClassType=resp["driverClassType"],
            parents=[],
            url=os.path.join(URL, "account", "data-connections"),
        )
    except Exception as e:
        node = dict(
            assetId=datastore_id, label="datastore", name="unknown", parents=[], note=str(e)
        )
    return node


def get_datasource_node(datasource_id, datastore_id, use_case_id):
    try:
        resp = client.get(f"externalDataSources/{datasource_id}").json()
        name = resp["canonicalName"]
        datastore_id = resp["params"]["dataStoreId"] if datastore_id is None else datastore_id
        node = dict(
            assetId=datasource_id,
            name=name,
            label="datasource",
            parents=[get_datastore_node(datastore_id, use_case_id)],
            url=os.path.join(URL, "account", "data-connections"),
        )
    except Exception as e:
        node = dict(
            assetId=datasource_id, name="unknown", label="datasource", parents=[], note=str(e)
        )
    return node


def get_recipe_node(recipe_id, use_case_id):
    resp = client.get(f"recipes/{recipe_id}").json()
    inputs = resp["inputs"]
    parents = []
    for input in inputs:
        if input["inputType"] == "datasource":
            node = get_datasource_node(input["dataSourceId"], input["dataStoreId"], use_case_id)
        elif input["inputType"] == "dataset":
            node = get_dataset_node(input["datasetId"], input["datasetVersionId"], use_case_id)
        parents.append(node)
    url = os.path.join(URL, "usecases", use_case_id, "wrangler", recipe_id)
    return dict(assetId=recipe_id, label="recipes", parents=parents, url=url, name=resp["name"])


def get_dataset_node(dataset_id, dataset_version_id=None, use_case_id=None):
    try:
        if dataset_version_id:
            pass
        else:
            print("no version id provided!! using latest version as default")
            dataset = dr.Dataset.get(dataset_id)
            dataset_version_id = dataset.version_id

        dataset = client.get(f"datasets/{dataset_id}/versions/{dataset_version_id}").json()
        recipe_id = dataset.get("recipeId")
        datasource_id = dataset.get("dataSourceId")
        data_engine_query_id = dataset.get("dataEngineQueryId")
        parents = []
        if recipe_id is not None:
            parents.append(get_recipe_node(recipe_id, use_case_id))
        if datasource_id is not None:
            parents.append(get_datasource_node(datasource_id, None, use_case_id))
        if data_engine_query_id is not None:
            parents.append(dict(label="dataEngineQueries", assetId=data_engine_query_id))
        dataset_node = dict(
            assetId=dataset.get("datasetId"),
            assetVersionId=dataset.get("versionId"),
            label="datasets",
            name=dataset.get("name"),
            url=os.path.join(URL, "ai-catalog", dataset.get("datasetId")),
            parents=parents,
        )
    except Exception as e:
        dataset_node = dict(
            assetId=dataset_id,
            assetVersionId=dataset_version_id if dataset_version_id else "unknown",
            label="datasets",
            name="unknown",
            parents=[],
            note=str(e),
        )
    return dataset_node


def get_vectordatabase_node(vdb_id, use_case_id):
    try:
        vdb = dr.genai.VectorDatabase.get(vdb_id)
        try:
            dataset = dr.Dataset.get(vdb.dataset_id)
            dataset_version_id = (
                dataset.version_id
            )  ## dataset version id is not available from vdb.
            dataset_node = get_dataset_node(dataset.id, dataset_version_id, use_case_id=use_case_id)
            url = os.path.join(URL, "usecases", use_case_id, "vector-databases", vdb.id)
            vdb_node = dict(
                assetId=vdb.id,
                label="vectorDatabases",
                name=vdb.name,
                url=url,
                parents=[dataset_node],
            )
            # pprint.pprint(vdb_node)
            return vdb_node
        except Exception as e:
            print(e)
            print(vdb_id)
            return None
    except Exception as e:
        print(vdb_id)
        print(e)
        return None


def get_project_node(pid, use_case_id):
    try:
        project = dr.Project.get(pid)
        catalog_id = project.catalog_id
        label = "useCases" if catalog_id is None else "datasets"
        id = catalog_id if catalog_id else use_case_id
        versionId = project.catalog_version_id if catalog_id else None

        return dict(
            assetId=project.id,
            label="projects",
            name=project.project_name,
            url=os.path.join(URL, "projects", project.id),
            datasouce="registry" if catalog_id else "local",
            parents=[
                get_dataset_node(id, versionId, use_case_id),
                #  dict(label="useCases", id = use_case_id)
            ],
        )
    except Exception as e:
        print(e)
        return None


def get_model_node(dr_model, project_node):
    try:
        model_node = dict(
            assetId=dr_model.id,
            label="models",
            url=os.path.join(URL, "projects", dr_model.project_id, "models", dr_model.id),
            modelType=dr_model.model_type,
            modelFamily=dr_model.model_family,
            parents=[project_node],
        )
        return model_node
    except Exception as e:
        print(e)
        return None


def get_model_nodes(pid, use_case_id):
    try:
        project = dr.Project.get(pid)
        project_node = get_project_node(pid, use_case_id)
        model_nodes = [get_model_node(model, project_node) for model in project.get_model_records()]
        return model_nodes
    except Exception as e:
        print(e)
        return []


def get_custom_model_version_node(
    custom_model_id, custom_model_version_id=None, custom_model_version_label=None, use_case_id=None
):
    try:
        if custom_model_version_label:
            custom_model_versions = client.get(f"customModels/{custom_model_id}/versions").json()
            custom_model_version = [
                cm
                for cm in custom_model_versions["data"]
                if cm["label"] == custom_model_version_label
            ].pop()
            custom_model_version_id = custom_model_version["id"]
        elif custom_model_version_id:
            pass
        else:
            raise Exception("need either custom model version id or custommodel version label")
        url = os.path.join(
            URL,
            "registry",
            "custom-model-workshop",
            custom_model_id,
            "versions",
            custom_model_version_id,
        )
        return dict(
            assetId=custom_model_id,
            assetVersionId=custom_model_version_id,
            url=url,
            label="customModels",
            parents=[],
        )
    except Exception as e:
        print(e)
        return None


def get_registered_model_node(reg_model_id, reg_model_version_id, use_case_id):
    reg_model_version = client.get(
        f"registeredModels/{reg_model_id}/versions/{reg_model_version_id}"
    ).json()
    url = os.path.join(
        URL, "registry", "registered-models", reg_model_id, "version", reg_model_version_id, "info"
    )
    try:
        custom_model_id = reg_model_version["sourceMeta"]["customModelDetails"]["id"]
        custom_model_versions = client.get(f"customModels/{custom_model_id}/versions").json()
        custom_model_version = [
            cm
            for cm in custom_model_versions["data"]
            if cm["label"] == reg_model_version["sourceMeta"]["customModelDetails"]["versionLabel"]
        ].pop()
        custom_model_node = get_custom_model_version_node(
            custom_model_id, custom_model_version["id"]
        )
        node = dict(
            assetId=reg_model_id,
            assetVersionId=reg_model_version_id,
            url=url,
            label="customRegisteredModels",
            name=reg_model_version["name"],
            parents=[custom_model_node],
        )
        return node
    except Exception as e:
        project_id = reg_model_version["sourceMeta"]["projectId"]
        ## need to fix this so it returns an actual model node in the parents
        dr_model = dr.Model.get(project_id, reg_model_version["modelId"])
        project_node = get_project_node(project_id, use_case_id)
        model_node = get_model_node(dr_model, project_node)
        node = dict(
            assetId=reg_model_id,
            assetVersionId=reg_model_version_id,
            url=url,
            label="registeredModels",
            name=reg_model_version["name"],
            parents=[model_node],
        )
        return node


def get_deployment_node(dep_id, use_case_id):
    try:
        dep = dr.Deployment.get(dep_id)
        cm = dep.model.get("custom_model_image")
        mp = dep.model_package
        reg_model_id = mp["registered_model_id"]
        reg_model_name = mp["name"]
        try:
            reg_model_versions = client.get(f"registeredModels/{reg_model_id}/versions").json()[
                "data"
            ]
            reg_model_version = [v for v in reg_model_versions if v["name"] == reg_model_name].pop()
            reg_model_node = get_registered_model_node(
                reg_model_id, reg_model_version["id"], use_case_id
            )
        except Exception as e:
            print(e)
            print("cant retrieve reg model versions")
            reg_model_node = {"assetId": reg_model_id, "note": e}
        deployment_node = dict(
            assetId=dep.id,
            name=dep.label,
            label="deployments",
            url=os.path.join(URL, "console-nextgen", "deployments", dep.id, "overview"),
            parents=[reg_model_node],
        )
        return deployment_node
    except Exception as e:
        print(e)
        return None


def get_llm_node(llm_id):
    llm_node = llm = dict(assetId=llm_id, label="llm")
    return llm_node


def get_llm_blueprint_nodes(playground_id, use_case_id):
    llm_blueprints = client.get(
        "genai/llmBlueprints/", params={"playgroundId": playground_id}
    ).json()["data"]
    temp = []
    for llm_bp in llm_blueprints:
        url = os.path.join(
            URL, "usecases", use_case_id, "playgrounds", playground_id, "llmBlueprint", llm_bp["id"]
        )
        node = dict(
            assetId=llm_bp["id"],
            label="llmBlueprint",
            name=llm_bp["name"],
            url=url,
            parents=[
                get_vectordatabase_node(llm_bp["vectorDatabaseId"], use_case_id),
                get_llm_node(llm_bp["llmId"]),
                dict(
                    assetId=playground_id,
                    label="playgrounds",
                    url=os.path.join(
                        URL, "usecases", use_case_id, "playgrounds", playground_id, "comparison"
                    ),
                ),
            ],
        )
        llm = dict(id=llm_bp["llmId"], label="llm", name=llm_bp["llmName"])
        temp.append(node)
    return temp


import pprint


def define_id(node, parents):
    node_id = node["assetId"]
    parents = [p for p in parents if p]
    parents = [parent for parent in parents if parent.get("assetId")]
    if version := node.get("assetVersionId"):
        node["id"] = node_id + "-" + version
    else:
        node["id"] = node_id
    node["assetId"] = node_id
    if parents:
        for parent in parents:
            define_id(parent, parent.get("parents", []))
    else:
        pass


if __name__ == "__main__":
    args = parser.parse_args()

    use_case_id = args.use_case_id
    node_output_file = args.node_output_file
    edge_output_file = args.edge_output_file

    applications = client.get(f"useCases/{use_case_id}/applications").json()
    customApplications = client.get(f"useCases/{use_case_id}/customApplications").json()
    data = client.get(f"useCases/{use_case_id}/data").json()
    datasets = client.get(f"useCases/{use_case_id}/datasets").json()
    deployments = client.get(f"useCases/{use_case_id}/deployments").json()
    notebooks = client.get(f"useCases/{use_case_id}/notebooks").json()
    playgrounds = client.get(f"useCases/{use_case_id}/playgrounds").json()
    projects = client.get(f"useCases/{use_case_id}/projects").json()
    registeredModels = client.get(f"useCases/{use_case_id}/registeredModels").json()
    vector_databases = client.get(f"useCases/{use_case_id}/vectorDatabases").json()
    shared_roles = client.get(f"useCases/{use_case_id}/sharedRoles").json()
    recipes = {"data": []}
    for d in data["data"]:
        if d["entityType"] == "RECIPE":
            resp = client.get(f"recipes/{d['entityId']}").json()
            recipes["data"].append(resp)

    dataset_nodes = [
        get_dataset_node(d["datasetId"], d["versionId"], use_case_id) for d in datasets["data"]
    ]
    recipe_nodes = [get_recipe_node(r["recipeId"], use_case_id) for r in recipes["data"]]
    deployment_nodes = [get_deployment_node(d["id"], use_case_id) for d in deployments["data"]]
    vdb_nodes = [get_vectordatabase_node(d["id"], use_case_id) for d in vector_databases["data"]]
    project_nodes = [get_project_node(d["projectId"], use_case_id) for d in projects["data"]]
    model_nodes = [get_model_nodes(d["projectId"], use_case_id) for d in projects["data"]]
    registered_model_nodes = []
    for m in registeredModels["data"]:
        for v in m["versions"]:
            registered_model_nodes.append(get_registered_model_node(m["id"], v["id"], use_case_id))
    llm_bp_llm_nodes = [get_llm_blueprint_nodes(d["id"], use_case_id) for d in playgrounds["data"]]
    playground_nodes = [
        dict(
            assetId=p["id"],
            label="playgrounds",
            url=os.path.join(URL, "usecases", use_case_id, "playgrounds", p["id"], "comparison"),
            parents=[],
        )
        for p in playgrounds["data"]
    ]
    model_nodes = list(itertools.chain(*model_nodes))
    llm_bp_llm_nodes = list(itertools.chain(*llm_bp_llm_nodes))

    nodes = []
    nodes.extend(dataset_nodes)
    nodes.extend(recipe_nodes)
    nodes.extend(vdb_nodes)
    nodes.extend(project_nodes)
    nodes.extend(model_nodes)
    nodes.extend(registered_model_nodes)
    nodes.extend(deployment_nodes)
    nodes.extend(llm_bp_llm_nodes)
    nodes.extend(playground_nodes)

    nodes = [n for n in nodes if n]

    for i, node in enumerate(nodes):
        define_id(node, node.get("parents", []))
        nodes[i] = node

    for node in nodes:
        if node.get("versionId"):
            pass
        else:
            try:
                del node["versionId"]
            except:
                pass
    for node in nodes:
        for parent in node.get("parents", []):
            if parent:
                if parent.get("parentVersionId"):
                    pass
                else:
                    try:
                        del parent["parentVersionId"]
                    except:
                        pass

    for node in nodes:
        parents = node.get("parents", [])
        parents = [p for p in parents if p is not None]
        parents = [p for p in parents if p.get("assetId") is not None]
        node["parents"] = parents

    # print( f"length of datasets in node list is { len([d for d in nodes if d['label'] == 'datasets'])}")
    node_ids = [n["id"] for n in nodes]

    for node in nodes:
        node["color"] = "red"

    def add_parents_as_nodes(node, parents):
        for parent in parents:
            if parent is not None:
                if id := parent.get("id"):
                    if id in node_ids:
                        # print("parent already in node id list")
                        # print(parent)
                        pass
                    else:
                        # print("parent NOT already in node id list")
                        # print(parent)
                        nodes.append(parent)
                        node_ids.append(id)
                add_parents_as_nodes(parent, parent.get("parents", []))

    nodes_copy = copy.deepcopy(nodes)

    for node in nodes_copy:
        add_parents_as_nodes(node, node.get("parents", []))

    edges = []
    for node in nodes:
        parents = node.get("parents", [])
        parents = [] if parents is None else parents
        for parent in parents:
            try:
                edges.append({"from": parent["id"], "to": node["id"]})
            except Exception as e:
                pass

    for node in nodes:
        if node["assetId"] == "66683da40019e72defbc4dce":
            pprint.pprint(node)

    # nodes_deep_copy = []
    for i, node in enumerate(nodes):
        nodes[i] = copy.deepcopy(node)
    for node in nodes:
        parents = node.get("parents", [])
        for parent in parents:
            try:
                del parent["parents"]
            except Exception as e:
                pass

    import json

    with open(os.path.join(script_path, node_output_file), "w") as f:
        f.write(json.dumps(nodes))

    import json

    with open(os.path.join(script_path, edge_output_file), "w") as f:
        f.write(json.dumps(edges))
