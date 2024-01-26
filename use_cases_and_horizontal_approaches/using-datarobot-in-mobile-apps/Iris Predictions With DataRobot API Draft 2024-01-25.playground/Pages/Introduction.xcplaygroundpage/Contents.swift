/*:

 # Using DataRobot Predictions in Mobile Apps
 
 This playground demonstrates how to use DataRobot models in Swift for usin in iOS and iPadOS mobile applications. DataRobot provides a rich set of strategies for embedding models. This playground will demonstrate calling and processing respones from the [DataRobot Prediction API](https://docs.datarobot.com/en/docs/api/reference/predapi/dr-predapi.html). This is a realtime endpoint that is availbel for any models deployed on DataRobot even models developed externally but deployed to DataRobot.
 
 In addition to using the API, you can embed models directly in your apps code using specialized model types:
 
 1. **Eureqa:** [Eureqa models](https://docs.datarobot.com/en/docs/modeling/analyze-models/describe/eureqa.html) use algorithims to return human-readable and interpretable analytic expressions, which are easily reviewed by subject matter experts. The resultant model formula can essentially be copied directly into Swift for use in your applications.
 2. **Rulefit:** [Rulefit](https://docs.datarobot.com/en/docs/modeling/analyze-models/predictions/download.html#download-rulefit-code) models generate ML derived business logic. They natively generate Python code but their syntax can also be easily ported to Swift
 
 ## About the Data
 
 The data used in this example is the venerable Iris dataset. The Iris dataset measures the length and width of the petal and sepal of an Iris flower. The dataset can be used to identify the class of iris using various machine learning techniques.
  
 

*/




import TabularData

let dataPath = Bundle.main.url(forResource: "iris", withExtension: "csv")!
let irisData = try? DataFrame(contentsOfCSVFile: dataPath)

print(irisData!.columns)

import SwiftUI
import PlaygroundSupport
import Charts

struct SepalObservation: Identifiable {
    var petalWidth: Double
    var sepalWidth: Double
    var irisClass: String
    var id = UUID()
}

let chartData = irisData!.rows.map({(r) -> SepalObservation in return SepalObservation(petalWidth: r[3] as! Double, sepalWidth: r[1] as! Double, irisClass: r[4] as! String)})

struct SepalDataOverview: View {
    var body: some View {
        VStack(alignment: .leading) {
            Text("Overview of the Iris Petal & Sepal Data").font(.largeTitle).bold()
            
                VStack(alignment: .leading) {
                    Text("Number of Observations").font(.title3).bold()
                    Text(irisData!.shape.0.formatted()).padding(EdgeInsets(top: 0, leading: 8, bottom: 1, trailing: 2))
                    
                }
        
        VStack(alignment: .leading) {
            Text("Unique Species").font(.title3).bold()
            Text("3").padding(EdgeInsets(top: 0, leading: 8, bottom: 1, trailing: 2))
            
        }
            Spacer()
            Text("Compare Sepal & Petal Width by Iris Species").bold()
            Chart(chartData) {
                PointMark(
                    x: .value("Sepal Width", $0.sepalWidth),
                        y: .value("Petal Width", $0.petalWidth)
                ).foregroundStyle(by: .value("Iris Species", $0.irisClass))
                
            }
        }.padding(EdgeInsets(top: 0, leading: 20, bottom: 10, trailing: 20))
    }
}



PlaygroundPage.current.setLiveView(SepalDataOverview())


print(irisData!.summary())


//: [Next](@next)

 
