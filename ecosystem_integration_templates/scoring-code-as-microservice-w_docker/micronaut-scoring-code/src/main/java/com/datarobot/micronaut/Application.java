//Author: Pavel Ustinov
//Date: June 26th, 2023

package com.datarobot.micronaut;

import io.micronaut.runtime.Micronaut;

/**
 * The entry point of the application.
 */
public class Application {

  public static void main(String[] args) {
    Micronaut.run(Application.class, args);
  }
}
