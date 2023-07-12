//Author: Pavel Ustinov
//Date: June 26th, 2023

package com.datarobot.micronaut;

import java.io.File;
import java.io.IOException;
import java.io.StringReader;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.datarobot.prediction.IPredictorInfo;
import com.datarobot.prediction.IRegressionPredictor;
import com.datarobot.prediction.Predictors;
import com.opencsv.CSVReader;
import com.opencsv.CSVReaderBuilder;
import com.opencsv.exceptions.CsvException;

import io.micronaut.http.MediaType;
import io.micronaut.http.annotation.Body;
import io.micronaut.http.annotation.Controller;
import io.micronaut.http.annotation.Post;

@Controller("/score")
public class ScoringController {

    private IRegressionPredictor predictor;
    private static final Logger logger 
      = LoggerFactory.getLogger(ScoringController.class);

    @Post(consumes = MediaType.TEXT_PLAIN)
    public Predictions score(@Body String body) throws Exception {
        
        long start = System.nanoTime();
        List<Map<String, Object>> rowsToScore = readCsv(body);
        logger.info("Reading data from HTTP body took: {} ms", Math.round(System.nanoTime() - start)/1000000.0);

        start = System.nanoTime();
        loadModel();
        logger.info("Loading model took: {} ms", Math.round(System.nanoTime() - start)/1000000.0);
        
        start = System.nanoTime();
        List<Double> predictions = makePredictions(rowsToScore);
        logger.info("Scoring took: {} ms", Math.round(System.nanoTime() - start)/1000000.0);
        return new Predictions(predictions);

    }

    private List<Map<String, Object>> readCsv(String body) {
        List<String[]> allData = null;
        try (CSVReader csvReader = new CSVReaderBuilder(new StringReader(body))
                .build();) {
            allData = csvReader.readAll();
        } catch (IOException e) {
            logger.error("IOException", e.fillInStackTrace());
        } catch (CsvException e) {
            logger.error("CsvException", e.fillInStackTrace());
        }
        List<Map<String, Object>> listForScoring = new ArrayList<>();
        String[] header = allData.get(0);

        allData.subList(1, allData.size()).forEach(
                row -> {
                    Map<String, Object> sample = new HashMap<>();
                    for (int i = 0; i < header.length; ++i) {
                        sample.put(header[i], row[i]);
                    }
                    listForScoring.add(sample);
                });
        return listForScoring;
    }

    private void loadModel() throws Exception {
        String modelFolder = System.getenv("MODEL_FOLDER");
        if (modelFolder == null){
            modelFolder = "model";
            logger.info("Model folder has not been provided, using default 'model' folder.");
        }

        logger.info("Model folder: {}", modelFolder);
        File filePath = new File(modelFolder);

        try(Stream<File> stream = Stream.of(filePath.listFiles())){ 
            List<String> modelFilename = stream
                    .filter(file -> !file.isDirectory())
                    .map(File::getName)
                    .collect(Collectors.toList());
            logger.info("Model filename: {}", modelFilename.get(0));
            URL[] urls = new URL[] { new URL("file://" + filePath.getCanonicalPath() + "/" + modelFilename.get(0)) };
            logger.info("Path to model: {}", filePath.getCanonicalPath() + "/" + modelFilename.get(0));
            URLClassLoader urlClassLoader = new URLClassLoader(urls);
            IPredictorInfo predictorInfo = Predictors.getPredictor(urlClassLoader);

            if (!(predictorInfo instanceof IRegressionPredictor)) {
                throw new Exception("Provided model is not a Java regression model");
            }

            this.predictor = (IRegressionPredictor) predictorInfo;

        } catch (IOException e) {
            logger.error("Failed to load model.", e.fillInStackTrace());
            throw e;
        }
    }

    private List<Double> makePredictions(List<Map<String, Object>> rowsToScore) {
        List<Double> predictions = new ArrayList<>();

        rowsToScore.forEach(row -> {
            Double prediction = predictor.score(row);
            predictions.add(prediction);
        });
        return predictions;
    }

}
