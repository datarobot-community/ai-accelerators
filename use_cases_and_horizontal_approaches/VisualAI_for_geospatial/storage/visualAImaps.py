import os
from pathlib import Path
import zipfile

import datarobot as dr
import geopandas as gpd
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import rasterio as rio
from rasterio import mask
from rasterio.features import rasterize
from shapely import wkt
import yaml


def plot_raster(raster):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        rio.plot.show(np.log(raster.read(masked=True)))
    return None


def read_yaml_file(file_path):
    with open(file_path, "r") as file:
        try:
            data = yaml.safe_load(file)
            return data
        except yaml.YAMLError as exc:
            print(f"Error reading YAML file: {exc}")
            return None


def load_parameters(reg_dic):
    try:
        return {
            "reg": reg_dic["name"],
            "reg_crs": reg_dic["crs"],
            "reg_chip": reg_dic["modelling"]["chip_length"],
            "reg_exclusion": reg_dic["modelling"]["exclusion_zone"],
            "reg_prop_random": reg_dic["modelling"]["proportion_random_points"],
        }
    except KeyError as e:
        raise KeyError(f"Missing required parameter: {e}")


def load_rasters(reg_dic, reg):
    try:
        Path("aux").mkdir(parents=True, exist_ok=True)
        raster_names = []
        rasters = []
        for raster in reg_dic["rasters"].keys():
            raster_names.append(raster)
            rasters.append(rio.open(reg_dic["rasters"][raster], "r+"))
        if "gpd_maps" in reg_dic.keys():
            for map in reg_dic["gpd_maps"].keys():
                raster_names.append(map)
                rasterised = rasterise_gpd(
                    gpd.read_file(reg_dic["gpd_maps"][map]),
                    reg_dic["crs"],
                    rasters[0].shape,
                    reg + map,
                    "aux",
                )
                rasters.append(rasterised)
        return raster_names, rasters
    except Exception as e:
        raise Exception(f"Error loading rasters: {e}")


def load_and_process_facilities(reg_dic, params, reg_outline):
    try:
        facilities = pd.read_csv(reg_dic["facilities"], encoding="latin-1")
        facilities = facilities_to_gpd(facilities, params["reg_crs"], reg_outline)
        return facilities_gdp_to_cells(facilities, params["reg_chip"], [])
    except Exception as e:
        raise Exception(f"Error loading and processing facilities: {e}")


def add_raster_data_to_training_data(training_data, raster_names, rasters, reg_path_images):
    for j in range(len(raster_names)):
        training_data[raster_names[j]] = ""
        for i, row in training_data.iterrows():
            row_index = i
            name = raster_names[j] + str(row_index) + ".png"
            path = reg_path_images + name
            point = row.geometry
            generate_chip(point, rasters[j], path)
            training_data.at[i, raster_names[j]] = "/images/" + name

    return training_data


def add_raster_data_to_scoring_data(training_data, raster_names, rasters, reg_path_images):
    for j in range(len(raster_names)):
        training_data[raster_names[j]] = ""
        for i, row in training_data.iterrows():
            row_index = i
            name = raster_names[j] + str(row_index) + ".png"
            path = reg_path_images + name
            point = row.geometry
            generate_chip(point, rasters[j], path)
            training_data.at[i, raster_names[j]] = reg_path_images + name

    return training_data


def create_training_data(reg_dic):
    try:
        params = load_parameters(reg_dic)
        reg_outline = get_country_outline(params["reg"], params["reg_crs"], 5)

        facilities_cells = load_and_process_facilities(reg_dic, params, reg_outline)
        no_facilities_cells = negative_cells(
            facilities_cells,
            params["reg_prop_random"],
            params["reg"],
            params["reg_chip"],
            params["reg_exclusion"],
        )
        training_data = pd.concat(
            [facilities_cells, no_facilities_cells], join="inner"
        ).reset_index(drop=True)

        raster_names, rasters = load_rasters(reg_dic, params["reg"])

        # first, make sure we have a path to write to:
        OUTPUT_FOLDER = "TEMP/"
        reg_path = OUTPUT_FOLDER + str(params["reg"])
        reg_path_images = reg_path + "/images/"
        Path(reg_path_images).mkdir(parents=True, exist_ok=True)

        # This step crops all the rasters to agree with each cell, saves the cropped images and adds the paths to these images.
        training_data = add_raster_data_to_training_data(
            training_data, raster_names, rasters, reg_path_images
        )
        # we don't want to use the geometry column for training!
        training_data.drop(columns=["geometry"], inplace=True)
        training_data.to_csv(reg_path + "/train.csv", index=False)

        with zipfile.ZipFile(
            OUTPUT_FOLDER + params["reg"] + ".zip", "w", zipfile.ZIP_DEFLATED
        ) as zipf:
            zipdir(reg_path, zipf)

        return zipf, reg_path + ".zip"

    except Exception as e:
        print(f"Error creating training data: {e}")
        return None


def create_scoring_data(reg_dic, sampling=1):
    # the sampling parameter allows us to only sample random cells to save time
    try:
        params = load_parameters(reg_dic)
        reg_outline = get_country_outline(params["reg"], params["reg_crs"], 5)

        raster_names, rasters = load_rasters(reg_dic, params["reg"])

        # first, make sure we have a path to write to:
        OUTPUT_FOLDER = "SCORING/"
        reg_path = OUTPUT_FOLDER + str(params["reg"])
        reg_path_images = OUTPUT_FOLDER + str(params["reg"]) + "/images/"
        Path(reg_path_images).mkdir(parents=True, exist_ok=True)

        scoring_data = make_grid(reg_outline, params["reg_chip"] * 1000)
        scoring_data = gpd.GeoDataFrame(geometry=gpd.GeoSeries(scoring_data))
        scoring_data.columns = ["geometry"]
        scoring_data["inside_region"] = scoring_data.within(reg_outline)
        scoring_data = scoring_data[scoring_data["inside_region"] == True]
        scoring_data.drop(columns=["inside_region"], inplace=True)

        scoring_data = scoring_data.sample(int(sampling * scoring_data.shape[0]))

        # This step crops all the rasters to agree with each cell, saves the cropped images and adds the paths to these images.
        scoring_data = add_raster_data_to_scoring_data(
            scoring_data, raster_names, rasters, reg_path_images
        )

        scoring_data.to_csv(reg_path + "/scoring.csv", index=False)

        return reg_path, reg_path_images

    except Exception as e:
        print(f"Error creating training data: {e}")
        return None


def train_and_deploy_suitability_model(name, training_data_path, credentials):
    # pass the token and endpoint
    dr.Client(token=credentials[0], endpoint=credentials[1])
    project = dr.Project.create(training_data_path, project_name=name)
    print("https://app.datarobot.com/projects/" + project.id)
    project.analyze_and_model("target", worker_count=-1)
    print("waiting for autopilot to finish")
    project.wait_for_autopilot()
    top_model = project.get_models()[0]
    print("top model is: " + str(top_model))
    prediction_server = dr.PredictionServer.list()[0]
    prediction_server.id

    ## let's deploy the top model from the project
    deployment = dr.Deployment.create_from_learning_model(
        top_model.id,
        label="name",
        description="leverage visualAI to model spatial data",
        default_prediction_server_id=prediction_server.id,
    )

    print("https://app.datarobot.com/deployments/" + deployment.id)

    return project.id, deployment.id


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(
                os.path.join(root, file),
                os.path.relpath(os.path.join(root, file), os.path.join(path, "..")),
            )


def negative_cells(facilities, reg_prop_random, reg, reg_chip, reg_exclusion):
    df_rand_points = generate_points(
        num_points=int(len(facilities) * reg_prop_random),
        country_name=reg,
        CHIP_SIDE_LENGTH=reg_chip,
        df_hospitals=facilities,
        EXCLUSION_ZONE_RATIO=reg_exclusion,
    )

    no_facilities_cells = df_rand_points.copy()
    no_facilities_cells.geometry = no_facilities_cells.buffer(reg_chip * 1000 / 2, cap_style=3)

    no_facilities_cells["target"] = False

    return no_facilities_cells


def facilities_gdp_to_cells(facilities_gdp, chip_l, hosp_features):
    columns = ["_id", "geometry"]
    if len(hosp_features) > 0:
        columns = columns + hosp_features
    cells = facilities_gdp[columns].copy()
    cells.geometry = cells.buffer(chip_l * 1000 / 2, cap_style=3)

    cells["target"] = False
    if "vfmCompletenessScore" in columns:
        cells["target"] = cells["vfmCompletenessScore"] > 0
    else:
        cells["target"] = True

    return cells


def facilities_to_gpd(df_hospitals, crs, outline):
    # convert to gdp and ensure they are within the country/region outline
    df_hospitals_coordinates_xy = df_hospitals["coordinates.coordinates"].apply(lambda x: eval(x))
    df_hospitals_coordinates_x = df_hospitals_coordinates_xy.apply(
        lambda x: x[0] if isinstance(x[0], float) else 0
    )
    df_hospitals_coordinates_y = df_hospitals_coordinates_xy.apply(
        lambda x: x[1] if isinstance(x[1], float) else 0
    )
    df_hospitals = gpd.GeoDataFrame(
        df_hospitals,
        geometry=gpd.points_from_xy(x=df_hospitals_coordinates_x, y=df_hospitals_coordinates_y),
        crs="EPSG:4326",
    )
    df_hospitals = df_hospitals.to_crs(crs)
    df_hospitals["inside_outline"] = df_hospitals.within(outline)
    df_hospitals = df_hospitals[df_hospitals["inside_outline"] == True]
    return df_hospitals


def rasterise_gpd(gdf, crs, shape, name, path):
    # Define the output raster file format and options
    meta = {
        "driver": "GTiff",
        "dtype": "int16",
        "nodata": 0,
        "width": shape[1],
        "height": shape[0],
        "count": 1,
        "crs": crs,
        "transform": rio.transform.from_bounds(*gdf.total_bounds, 512, 512),
    }

    path_string = path + "/" + name + ".tif"
    # Create the output raster file
    with rio.open(path_string, "w", **meta) as out:
        # Rasterize the input shapefile into the output raster file
        shapes = ((geom, 1) for geom in gdf.geometry)
        out_arr = rasterize(shapes=shapes, fill=0, out_shape=(512, 512), transform=out.transform)
        out.write(out_arr, indexes=1)

    new_raster = rio.open(path_string)

    return new_raster


def reproject_raster(in_path, out_path, crs):
    """ """
    # reproject raster to project crs
    with rio.open(in_path) as src:
        src_crs = src.crs
        transform, width, height = rio.warp.calculate_default_transform(
            src_crs, crs, src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()

        kwargs.update({"crs": crs, "transform": transform, "width": width, "height": height})

        with rio.open(out_path, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                rio.warp.reproject(
                    source=rio.band(src, i),
                    destination=rio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=crs,
                    resampling=rio.warp.Resampling.nearest,
                )
    return out_path


def get_country_outline(country_name, crs, CHIP_SIDE_LENGTH=5):
    world_filepath = gpd.datasets.get_path("naturalearth_lowres")
    world = gpd.read_file(world_filepath).to_crs(crs)
    country_geom = (
        world.loc[world.name == country_name, "geometry"]
        .buffer(CHIP_SIDE_LENGTH)
        .reset_index(drop=True)
        .loc[0]
    )
    return country_geom


def generate_chip(point, raster, fname, cmap="viridis", **kwargs):
    df_chip = mask.mask(raster, [point], crop=True)[0][0]
    plt.imsave(fname=fname, arr=df_chip, cmap=cmap, **kwargs)


def generate_points(num_points, country_name, CHIP_SIDE_LENGTH, df_hospitals, EXCLUSION_ZONE_RATIO):
    this_crs = df_hospitals.crs
    bounding_box = get_country_outline(country_name, this_crs).bounds
    # generate random points within country bounding box
    x_coords = np.random.uniform(low=bounding_box[0], high=bounding_box[2], size=num_points)
    y_coords = np.random.uniform(low=bounding_box[1], high=bounding_box[3], size=num_points)
    df_points = gpd.GeoDataFrame(crs=this_crs, geometry=gpd.points_from_xy(x=x_coords, y=y_coords))
    # remove points outside of country area
    df_points = df_points[
        df_points.within(get_country_outline(country_name, this_crs))
    ].reset_index(drop=True)
    # remove points near existing hospitals
    df_points = exclude_points_near_hospitals(
        df_points, df_hospitals, CHIP_SIDE_LENGTH * EXCLUSION_ZONE_RATIO
    )
    return df_points


def exclude_points_near_hospitals(df_points, df_hospitals, exclusion_zone):
    this_df_exclusion = df_hospitals.copy()
    this_df_exclusion.geometry = df_hospitals.buffer(exclusion_zone)
    this_df_points = df_points.copy()
    this_df_points["index"] = this_df_points.index
    intersect_points = this_df_points.sjoin(this_df_exclusion, how="inner")["index"]

    return df_points[~this_df_points.index.isin(intersect_points)]


def add_hospital_negatives(df_hospitals, hospital_class_feature):
    cross_join_1 = df_hospitals[["_id", "geometry"]]
    cross_join_2 = pd.DataFrame(
        df_hospitals[hospital_class_feature].unique(), columns=[hospital_class_feature]
    )

    cross_join_1["key"] = 0
    cross_join_2["key"] = 0

    df_hospital_overlaps = (
        gpd.overlay(df_hospitals, df_hospitals, how="intersection")
        .groupby(["_id_1", f"{hospital_class_feature}_2"])["_id_2"]
        .count()
        .reset_index()
    )

    df_hospital_w_target = cross_join_1.merge(cross_join_2, on="key", how="outer")
    df_hospital_w_target = df_hospital_w_target.merge(
        right=df_hospital_overlaps,
        how="left",
        left_on=["_id", hospital_class_feature],
        right_on=["_id_1", f"{hospital_class_feature}_2"],
    )

    # Should we drop the non-identity positive records in here? This should be the exclusivity point?
    # Also should we change how true / false are defined (e.g. is class 3 also suitable for class 2 and 1, currently no, it's not)

    df_hospital_w_target["suitability"] = ~df_hospital_w_target["_id_1"].isnull()
    df_hospital_w_target = df_hospital_w_target[
        ["_id", "geometry", hospital_class_feature, "suitability"]
    ]
    return df_hospital_w_target


def make_grid(polygon, edge_size):
    """
    polygon : shapely.geometry
    edge_size : length of the grid cell
    """
    from itertools import product

    import geopandas as gpd
    import numpy as np

    bounds = polygon.bounds
    x_coords = np.arange(bounds[0] + edge_size / 2, bounds[2], edge_size)
    y_coords = np.arange(bounds[1] + edge_size / 2, bounds[3], edge_size)
    combinations = np.array(list(product(x_coords, y_coords)))
    squares = gpd.points_from_xy(combinations[:, 0], combinations[:, 1]).buffer(
        edge_size / 2, cap_style=3
    )

    return gpd.GeoSeries(squares[squares.intersects(polygon)])


def predictions_scoring_data(credentials, deployment_id, scoring_data_path):
    # pass the token and endpoint
    dr.Client(token=credentials[0], endpoint=credentials[1])

    job = dr.BatchPredictionJob.score(
        deployment=deployment_id,
        include_prediction_status=True,
        intake_settings={
            "type": "localFile",
            "file": scoring_data_path,
        },
        output_settings={
            "type": "localFile",
            "path": "./results.csv",
        },
        # If explanations are required, uncomment the line below
        # max_explanations=3,
        # If text explanations are required, uncomment the line below.
        # max_ngram_explanations='all',
        # Uncomment this for Prediction Warnings, if enabled for your deployment.
        # prediction_warning_enabled=True
    )

    job.wait_for_completion()

    results = pd.read_csv("results.csv")

    df = pd.read_csv(scoring_data_path)
    df["prediction"] = results["target_True_PREDICTION"]
    df["geometry"] = df["geometry"].apply(wkt.loads)
    gdf = gpd.GeoDataFrame(df)

    return gdf
