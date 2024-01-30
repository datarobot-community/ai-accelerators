# DataRobot-Hosted Object Detection

This repo includes two notebooks in support of accelerating object detection use cases
1. `FasterR-CNN_training.ipynb`: create a scratch detection FasterR-CNN network, including data preprocess, training, and evaluation.
2. `object_detection_custom_model.ipynb`: leverage the broad capabilities of DataRobot ML Production by deploying the model trained in 1. into a custom model enviroment.

## Guidance

1. Clone the repository to your local machine.
2. It is recommended to run through the entire workflow using the provided sample data before adapting to new datasets, class ontology, ground truth formats, etc. The notebooks contain steps for downloading the required data.
3. Start with `FasterR-CNN_training.ipynb` to train a new model.
4. Proceed to `object_detection_custom_model.ipynb` using the newly trained model.
5. (optional) explore additional custom metrics for the DataRobot deployment.
6. Adapt the workflow to new datasets


<!-- ## Contributing

We welcome contributions! Please see our [contributing guidelines](CONTRIBUTING.md) for more details.

## License

This project is licensed under the terms of the Apache License 2.0. For more details, please see the [LICENSE](LICENSE) file.

## Support

For any questions or issues, please contact the maintainers, or raise an issue in the GitHub repository. -->
