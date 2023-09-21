//Author: Pavel Ustinov
//Date: June 26th, 2023

package com.datarobot.micronaut;

import java.util.List;

/**
 * Predictions class.
 */
public class Predictions {

  private final List<Double> predictions;

  public Predictions(List<Double> predictions) {
    this.predictions = predictions;
  }

  public List<Double> getPredictions() {
    return predictions;
  }
}
