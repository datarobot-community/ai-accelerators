// Import the built-in 'http' module
const http = require('http');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const port = 8000;

// const datarobotEndpoint = "https://app.datarobot.com/api/v2"
// const datarobotToken = process.env.DATAROBOT_API_TOKEN
var datarobotEndpoint = null
var datarobotToken = null
var useCaseId = null

// Run a Python script and return output
function runPythonScript(scriptPath, args, callback) {
  // Use child_process.spawn method from 
  // child_process module and assign it to variable
  const pyProg = spawn('python3', [scriptPath].concat(args));

  // Collect data from script and print to console
  let data = '';
  pyProg.stdout.on('data', (stdout) => {
    data += stdout.toString();
  });

  // Print errors to console, if any
  pyProg.stderr.on('data', (stderr) => {
    console.log(`stderr: ${stderr}`);
  });

  // When script is finished, print collected data
  pyProg.on('close', (code) => {
    if (code !== 0) {
      console.log(`python script exited with code ${code}`)
      callback(`Error: Script existed with code ${code}`, null)
    } else {
      console.log(`Python script exited with code ${code}`)
      callback(null, data)
    }
  });
}

// Create an HTTP server
const server = http.createServer((req, res) => {

  let filePath = path.join(__dirname, req.url === '/' ? 'index.html' : req.url);
  console.log(`filepath: ${filePath}`)
  const extname = path.extname(filePath);

  const url = req.url;
  const method = req.method;
  console.log(`url is ${req.url}`)
  if (method === 'POST') {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    })
    req.on('end', () => {
      const config = JSON.parse(body)
      const envVar = `DATAROBOT_API_TOKEN=${config["token"]}\nDATAROBOT_ENDPOINT=${config["endpoint"]}`
      fs.writeFileSync(path.join(__dirname, ".env"), envVar)
      runPythonScript(path.join(__dirname, "create_use_case_file.py"), [], (err, result) => {
        if (err) {
          console.error(`error -> ${err}`)
          res.writeHead(400, { "Content-Type": "application/json" })
          res.end(JSON.stringify({ message: `Something went wrong: ${err}` }), 'utf-8')
        } else {
          console.log("use case list is complete")
          res.writeHead(200, { 'Content-Type': 'application/json' })
          const data = fs.readFileSync(path.join(__dirname, "./use_case_list.json"), "utf-8")
          res.end(data, 'utf-8')
        }
      })
    })
      ;
  } else if (url === "/" && method === 'GET') {
    // console.log(`url: ${url}`)
    let indexFilePath = path.join(__dirname, "index.html")
    // console.log(`index.html is located at ${indexFilePath}`)
    fs.readFile(indexFilePath, (err, content) => {
      if (err) {
        console.log(err)
        res.writeHead(404, { 'Content-Type': 'text/html' });
        res.end('<h1>404 Not Found</h1>', 'utf-8');
      } else {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(content, 'utf-8');
        console.log(`${url}: result should have been returned\n`)
      }
    })
  } else if (url.includes("/useCases")) {
    console.log(`url was a match ${url}`)
    useCaseId = url.split("/").pop()
    console.log(`recieved use case ${useCaseId}`)
    console.log("running python script to create graph")
    const edge_output_file = path.join(__dirname, `${useCaseId}_edges.json`)
    const node_output_file = path.join(__dirname, `${useCaseId}_nodes.json`)
    if (!fs.existsSync(node_output_file)) {
      runPythonScript(path.join(__dirname, "create_graph_from_use_case.py"), [
        "--use-case-id", useCaseId,
        "--node-output-file", node_output_file,
        "--edge-output-file", edge_output_file], (err, result) => {
          if (err) {
            console.error(`error -> ${err}`)
            res.writeHead(404, { "Content-Type": "text/plain" })
            res.end("non zero exit from python script", "utf-8")
          } else {
            console.log("script is complete, wait for graph to update")
            console.log("finished running script")
            res.writeHead(200, { 'Content-Type': 'text/plain' })
            res.end("refresh", 'utf-8')
          }
        })
    } else {
      console.log(`${node_output_file} exists`)
      res.writeHead(200, { 'Content-Type': 'text/plain' })
      res.end("refresh", 'utf-8')
    }
  } else if (url.includes("/getUseCases")) {
    console.log("get use case list request recieved")
    if (fs.existsSync(path.join(__dirname, "./use_case_list.json"))) {
      console.log("use case list file exists.  will load directly without calling python script")
      res.writeHead(200, { 'Content-Type': 'application/json' })
      const data = fs.readFileSync(path.join(__dirname, "./use_case_list.json"), "utf-8")
      res.end(data, 'utf-8')
    } else {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end("[]", 'utf-8')
    }
  } else if (url.includes("/getNodes")) {
    console.log("get nodes request recieved")
    res.writeHead(200, { 'Content-Type': 'application/json' })
    const data = fs.readFileSync(path.join(__dirname, `${useCaseId}_nodes.json`), "utf-8")
    // const jsonData = JSON.parse(data)
    res.end(data, 'utf-8')
  } else if (url.endsWith("/getEdges")) {
    console.log("get edges request recieved")
    res.writeHead(200, { 'Content-Type': 'application/json' })
    const data = fs.readFileSync(path.join(__dirname, `${useCaseId}_edges.json`), "utf-8")
    // const jsonData = JSON.parse(data)
    res.end(data, 'utf-8')
  } else if (extname == "json") {
    contentType = 'application/json';
    res.writeHead(200, { 'Content-Type': 'application/json' })
    const data = fs.readFileSync(filePath, "utf-8")
    console.log(`filepath requests = ${filePath}`)
    res.end(data, 'utf-8')
  } else {
    let contentType = 'text/html';
    if (extname === '.js') {
      contentType = 'application/javascript';
    } else if (extname === '.css') {
      contentType = 'text/css';
    }
    // Read the file and send it as the response
    fs.readFile(filePath, (err, content) => {
      if (err) {
        res.writeHead(404, { 'Content-Type': 'text/html' });
        res.end('<h1>404 Not Found</h1>', 'utf-8');
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content, 'utf-8');
      }
    })
  };
});

// Start the server on port 8000
server.listen(port, () => {
  console.log(`Server running at http://localhost:${port}/`);
});
