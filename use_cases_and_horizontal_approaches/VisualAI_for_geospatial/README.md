## Leveraging Visual AI for geospatial data.

Here we show how we can use Visual AI on geospatial data. Instead of deriving numeric features from the georeferenced data, we look at the geospatial data as images. For example, if we have a map of population distribution, instead of extracting the population that corresponds to each row of our main table we can pass the region of the map that corresponds to that row. This provides more information than a raw count of the population would, as it also encodes the distribution within the region (is it uniform or does it concentrate in some areas? what is the shape?, etc.)

The example we will use to illustrate the approach comes from work we have done with the Virtue Foundation (https://virtuefoundation.org/2021/05/virtue-foundation-datarobot-ai-conference/). As part of the "Data Mapping Initiative" we have built models to identify suitable locations for new healthcare facilities. By looking at the location of existing hospitals and clinics as a function of several features (road networks, population, terrain, etc.) we find which other areas are suitable in terms of these features (similar to a propensity model).

This work has been peer reviewed and published at the 2023 IEEE International Conference on Imaging Systems and Techniques (IST) (https://ieeexplore.ieee.org/abstract/document/10355652)

This repository contains:

- A jupyter notebook that illustrates the approach.
- A python file (mini package) with all the functions required to run the notebook.
