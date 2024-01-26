//: [Previous](@previous)

/*:
## Using DataRobot Deployments

 Using DataRobot, create a deployment of the best model that can predict the Iris species based on the data provided.
 
 You can access a copy of the data directly at [this link](https://s3.amazonaws.com/datarobot_public_datasets/iris_friendly_names.csv)
 
 A quick caveat, I don't write Swift code often and there are certainly ways to improve this code flow. But in a matter of just an hour, you can integreate the DataRobot Model directly into Swift UI and so its so fast to get started.
 
 Plus, integrating the API means that DataRobot handles all the model management from use trakcing, retraining, and model version control.
 
 ### Defining Data Structures
 
 Because this is Swift, we need to define a few data types. First, let's define the structure of the data we will be sending into DataRobot's API

*/
import SwiftUI
import PlaygroundSupport

struct IrisInputData: Codable {
    var sepalLength: Double
    var sepalWidth: Double
    var petalLength: Double
    var petalWidth: Double
    
    private enum CodingKeys : String, CodingKey {
        case sepalLength = "sepal length"
        case sepalWidth = "sepal width"
        case petalLength = "petal length"
        case petalWidth = "petal width"
        
      }
}

/*:
Next we will define a strucuture for DataRobot's return values for Multiclass models. These object types are usableby any multiclass deployment. The raw response from the API will look something like this:
 
 ```
 {"data":
    [
    {"rowId":0,"prediction":"Iris-versicolor",
        "predictionValues":     [{"label":"Iris-setosa","value":0.1548547745},
            {"label":"Iris-versicolor","value":0.8050370216},
            {"label":"Iris-virginica","value":0.0401082672}],"deploymentApprovalStatus":"APPROVED"
    }]}
 
 ```

*/

struct MultiClasslabels: Codable {
    var label: String
    var value: Double
    
}

struct MultiClassResult: Codable {
    var rowId: Int
    var prediction: String
    var predictionValues: [MultiClasslabels]
    var deploymentApprovalStatus: String
}

struct MultiClassResults: Codable {
    var data: [MultiClassResult]
    
}

enum PredictionError: Error  {
    case runtimeError(String)
}

/*:
 
 ### Using URLRequest to Access API
 
 This class provides a simple way to sending the request to the DataRobot API via the `makePrediction` method defined.
 
 Note that to call the API you need three elemnts an API Token, A Deployment ID and a DEployment KEy
 
 */
class DRPredictor {
    private let url_session =   URLSession.init(configuration: URLSessionConfiguration.default, delegate: nil, delegateQueue: nil)
     var sender: URLRequest

    
     var token: String
     var authKey: String
    
    init(token: String, authKey: String, deploymentID: String)  {
        self.token = token
        self.authKey = authKey
        sender =  URLRequest(url: URL(string: "https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/\(deploymentID)/predictions" )!)
        sender.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        sender.setValue(self.authKey, forHTTPHeaderField: "DataRobot-Key")
        sender.setValue("application/json", forHTTPHeaderField: "Content-Type")
        sender.setValue("application/json", forHTTPHeaderField: "Accept")
        sender.httpMethod = "POST"
        
    }
    @MainActor func makePrediction(input: IrisInputData) async -> String {
           
           do {
               
               let (data, response) = try await url_session.upload(for: sender, from: JSONEncoder().encode([input]))
       
                   let resp = try JSONDecoder().decode(MultiClassResults.self, from: data)
                   
                       
               return String(resp.data[0].prediction)
                           
                       
                       //                predObject.prediction = resp.prediction
                   
           } catch {
               print("Unexpected error: \(error).")
               PredictionError.runtimeError("Unable to get and parse prediction")
           }
        return ""
       }
   }

/*:
 
 ## Putting it All Together
 
 */
struct IrisPredictionView: View {
    @State var sepalLength: Double = 5.8
    @State var sepalWidth: Double = 3.05
    @State var petalLength: Double = 3.75
    @State var petalWidth: Double = 1.19
    @State var DRToken: String = ""
    @State var DRDeploymentID: String = ""
    @State var DRApiKey: String = ""
    @State var needDRCredentials: Bool = true
    @State var prediction: String = ""
    @State var isLoading: Bool = false
    
    
    
    var body: some View {
        VStack(alignment: .leading){
        HStack(){
            Text("Iris Measurements").font(.system(size: 28, weight: Font.Weight.bold))
        Image(systemName: "camera.macro.circle").font(.system(size:60)).foregroundColor(Color.purple)
        }
        HStack {
            Text("Sepal Length: ")
            Slider(value: $sepalLength, in: 4.3...7.9)
            Text("\(sepalLength)")
        }
        HStack {
            Text("Sepal width: ")
            Slider(value: $sepalWidth, in: 1.0...8.0)
            Text("\(sepalWidth)")
        }
        HStack {
            Text("Petal width: ")
            Slider(value: $petalWidth, in: 1.0...8.0)
            Text("\(petalWidth)")
        }
        HStack {
            Text("Petal length: ")
            Slider(value: $petalLength, in: 1.0...8.0)
            Text("\(petalLength)")
        }
        Button("Submit") {
            Task{
                isLoading = true
                var result = await makePrediction()
            prediction = result
                isLoading = false}
        }.buttonStyle(.borderedProminent)
        Spacer()
            if(isLoading) {
                ProgressView()
            }else {
            HStack(){
                Text("DataRobot predicts this flower is: ").font(.caption)
                Text(prediction).font(.title).foregroundStyle(Color.purple)}
            }
        Spacer()
            .sheet(isPresented: $needDRCredentials, content: {
                VStack(alignment:.leading) {
                    Text("Please Provide Your DataRobot Credentials and Deployment Information").bold().font(.title3)
                                       TextField(
                        "DataRobot API Token",
                        text: $DRToken
                                       ).padding(EdgeInsets(top: 2, leading: 8, bottom: 1, trailing: 8)).textFieldStyle(.roundedBorder)
                    TextField(
                        "DataRobot API Key",
                        text: $DRApiKey
                    ).padding(EdgeInsets(top: 2, leading: 8, bottom: 1, trailing: 8)).textFieldStyle(.roundedBorder)
                    TextField(
                        "DataRobot Deployment ID ",
                        text: $DRDeploymentID
                    ).padding(EdgeInsets(top: 2, leading: 8, bottom: 1, trailing: 8)).textFieldStyle(.roundedBorder)
                    Button("Submit") {
                        needDRCredentials = false
                    }
                }.padding(EdgeInsets(top: 2, leading: 8, bottom: 1, trailing: 8)).buttonStyle(.borderedProminent)
            })
        
        }.padding(EdgeInsets(top: 5, leading: 20, bottom: 10, trailing: 20))
    }
    func makePrediction() async -> String  {
      
        let predictor = DRPredictor(token: DRToken, authKey: DRApiKey, deploymentID: DRDeploymentID)
        let result = await predictor.makePrediction(input: IrisInputData(sepalLength: sepalLength, sepalWidth: sepalWidth, petalLength: petalLength, petalWidth: petalWidth))
    
        return result
        
        
    }
}


PlaygroundPage.current.setLiveView(IrisPredictionView())






