// const container = document.getElementById('network');
// made a changes
var edges = null;
var nodes = null;
var subEdges = null;
var subNodes = null;
var visibleNodes = []
var activeNodeId = null

var nodesFilter = (node) => {
  return visibleNodes.includes(node.id)
};
const edgesFilter = (edge) => { 
  return true 
}

function toggleSidebar() {
  console.log("anything?")
  const sidebar = document.getElementById('right-sidebar');
  console.log(sidebar.innerText)
  sidebar.classList.toggle('collapsed');
}
var nodesDataset = new vis.DataSet(nodes)
var edgesDataset = new vis.DataSet(edges)
var nodesView = new vis.DataView(nodesDataset, { filter: nodesFilter });
var edgesView = new vis.DataView(edgesDataset, { filter: edgesFilter });
const dataView = {edges: edgesView, nodes: nodesView}


var container = document.getElementById("network");
// container.innerText = "Give us a moment while we grab your use cases from DataRobot"
var data = {edges: edges, nodes: nodes}

const artifactList = document.getElementById("artifact-list") 

const useCasesDropdown = document.getElementById('use-cases'); // Replace 'myuseCasesDropdown' with the ID of your useCasesDropdown
const useCasesRet = await fetch("getUseCases")
const useCases = await useCasesRet.json()
if (useCases.length > 0) { 
  for (const useCase of useCases) {
    const option = document.createElement('option');
    option.value = useCase.id; // Assuming your JSON has a 'value' field
    option.text = useCase.name;  // Assuming your JSON has a 'text' field
    useCasesDropdown.appendChild(option);
  }
}

document.querySelectorAll('.list-item').forEach(item => {
  item.addEventListener('click', function (e) {
      const nestedList = this.querySelector('.nested-list');
      if (nestedList && nestedList.contains(e.target)) {
          // If a nested-list item is clicked
          const clickedItem = e.target;
            const value = clickedItem.getAttribute('value');
            if (value) {
                alert(`Value: ${value}`);
            }
      } else if (nestedList) {
          // If a parent list-item with a nested list is clicked
          e.stopPropagation(); // Prevent event propagation
          nestedList.style.display = nestedList.style.display === 'block' ? 'none' : 'block';
      } else {
          // Leaf node without nested list
          // console.log('what did the five fingers say to the face!');
      }
  });
});

var apiConfigured = false
const configureApi = document.getElementById("configure-api")
configureApi.onclick = function () { 
  apiConfigured = !apiConfigured 
  const title = document.getElementById("configure-api-title")
  const token = document.getElementById("api-token")
  const tokenLabel = document.getElementById("api-token-label")
  const endpoint = document.getElementById("endpoint")
  const endpointLabel = document.getElementById("endpoint-label")
  title.innerText = apiConfigured ? "API Configuration" : ""
  token.style.display = apiConfigured ? "" : "none"
  tokenLabel.style.display = apiConfigured ? "" : "none"
  endpoint.style.display = apiConfigured ? "" : "none"
  endpointLabel.style.display = apiConfigured ? "" : "none"

}

var grabUseCases = document.getElementById("get-use-cases")
grabUseCases.onclick = function () { 
  container.innerText = "Grabbing your use cases from DataRobot.  This might take a minute"
  const token = document.getElementById("api-token")
  // token.style.display = "none"
  const tokenLabel = document.getElementById("api-token-label")
  // tokenLabel.style.display = "none"
  const endpoint = document.getElementById("endpoint")
  const endpointLabel = document.getElementById("endpoint-label")
  // endpoint.style.display = "none"
  // endpointLabel.style.display = "none"
  const data = JSON.stringify( {
    token:token.value, 
      endpoint:endpoint.value
  })
  fetch("datarobotAuth", {
    headers: {'Content-Type': "application/json"},
    method: 'POST',
    body: data,
    redirect: "follow"}).then(
      (response) => response.json()
    ).then(
      (useCases) => {
        useCasesDropdown.options.length = 0;
        for (const useCase of useCases) {
          const option = document.createElement('option');
          option.value = useCase.id; // Assuming your JSON has a 'value' field
          option.text = useCase.name;  // Assuming your JSON has a 'text' field
          useCasesDropdown.appendChild(option);
        }
        container.innerText = "Select a use case from the drop down box"
      }
    ).catch(
      (error) => {
        container.innerText = `${error}\nThere was a problem fetching your use cases.  are you sure you provded the correct api token and endpoint?`
        console.error("there was a problem")
      }
    );
};

const resetGraph = document.getElementById("reset-button")
resetGraph.onclick = function () { 
  draw(true)
}

var directedGraphToggleOn = false
const directedGraphToggle = document.getElementById("directed-graph-toggle")
directedGraphToggle.onclick = function () { 
  directedGraphToggleOn = ! directedGraphToggleOn
  btnUD.style.display = directedGraphToggleOn ? "" : "none"
  btnDU.style.display = directedGraphToggleOn ? "" : "none"
  btnLR.style.display = directedGraphToggleOn ? "" : "none"
  btnRL.style.display = directedGraphToggleOn ? "" : "none"
  draw(false)
}

var directionInput = document.getElementById("direction");
var btnUD = document.getElementById("btn-UD");
btnUD.onclick = function () {
  directionInput.value = "UD";
  draw(false);
};
var btnDU = document.getElementById("btn-DU");
btnDU.onclick = function () {
  directionInput.value = "DU";
  draw(false);
};
var btnLR = document.getElementById("btn-LR");
btnLR.onclick = function () {
  directionInput.value = "LR";
  draw(false);
};
var btnRL = document.getElementById("btn-RL");
btnRL.onclick = function () {
  directionInput.value = "RL";
  draw(false);
};

function draw(resetFilter = true) { 
  var container = document.getElementById("network")
  var options = graphOptions()
  var data = {
    nodes: nodes, 
    edges: edges
  }
  if (resetFilter) {
    for(let i = 0; i < nodes.length; i++){
      visibleNodes.push(nodes[i].id)
    }
  } 
  
  edgesDataset = new vis.DataSet(edges)
  nodesDataset = new vis.DataSet(nodes)
  edgesView = new vis.DataView(edgesDataset, { filter: edgesFilter })
  nodesView = new vis.DataView(nodesDataset, { filter: nodesFilter })
  var network = new vis.Network(container, {nodes: nodesView, edges: edgesView}, options);

  network.on('click', function (event) {
    const { nodes: selectedNodes } = event;
    const node = nodes.filter(n => n.id == selectedNodes)[0];
    activeNodeId = node.id || null
    console.log(`logging active node id ${activeNodeId}`)
    if (selectedNodes.length > 0) {
      const nodeInfo = [];
      nodeInfo.push(`<strong>Node Details</strong> <br>`)
      const keys = Object.keys(node)
      for (let i = 0; i < keys.length; i++) {
        let k = keys[i]
        if (k === "url") { 
          nodeInfo.push(`<strong>${k}</strong><p><a href="${node[k]}">see asset in Datarobot</a> </p> <br>`)
        } else if (k == "parents") {
          nodeInfo.push(`<strong>parents</strong><pre id="json">${JSON.stringify(node[k], null, 2)}</pre> <br>`)
        } else {
          nodeInfo.push(`<strong>${k}</strong><p>${node[k]}</p> <br>`)
        }
      }
      sideBarContent.innerHTML = nodeInfo.join(``)
      // sideBarContent.appendChild(emailInput);
      // sideBarContent.appendChild(shareButton);
      sideBarContent.appendChild(exportButton)
      
    }
  })

  network.on('doubleClick', function (event) {
    const { nodes: selectedNodes } = event;
    let edgeList = edgesDataset.get()
    for(let i = 0; i <= edgeList.length; i++){
      let currentEdge = edgeList[i]
      if (currentEdge) { 
        if (selectedNodes[0] == edgeList[i].from){
          visibleNodes.push(edgeList[i].to)
        } else if (selectedNodes[0] == edgeList[i].to) {
          visibleNodes.push(edgeList[i].from)
        } else {
          console.log("no match found")
        }
      } else { 
        console.log("edge appears to be undefined")
      }

    }
    nodesView.refresh()
    edgesView.refresh()
  })
}

function getNode(id) { 
  for(let j = 0; j <= nodes.length; j++) { 
    if(nodes[j].id == id) {
      return nodes[j]
    }
  }
}

function getParents(id) { 
  let parentNodes = []
  function helper(id) { 
    let n = getNode(id) 
    let parents = n.parents || []
    if(parents.length > 0) { 
      for(let j = 0; j < parents.length; j++) {
        parentNodes.push( getNode(parents[j].id))
        helper(parents[j].id)
      }
    }
  }
  helper(id)
  console.log("logging parents from getParents funct")
  console.log(parentNodes)
  return parentNodes
}

function getChildren(id) { 
  let childrenNodes = []
  function helper(id) {
    for(let j = 0; j < edges.length; j++) { 
      if(id == edges[j].from) { 
        let child = getNode(edges[j].to)
        childrenNodes.push(child)
        helper(edges[j].to)
      }
    }
  }
  helper(id)
  return childrenNodes
}

function topologicalSort(nodes, edges) {
  const inDegree = {};
  const result = [];
  const queue = [];

  // Calculate in-degree of each node
  nodes.forEach(node => inDegree[node.id] = 0);
  edges.forEach(edge => inDegree[edge.to]++);

  // Add nodes with in-degree 0 to the queue
  for (const nodeId in inDegree) {
    if (inDegree[nodeId] === 0) {
      queue.push(nodeId);
    }
  }

  // Process nodes in topological order
  while (queue.length > 0) {
    const nodeId = queue.shift();
    result.push(getNode(nodeId));

    edges.forEach(edge => {
      if (edge.from === nodeId) {
        inDegree[edge.to]--;
        if (inDegree[edge.to] === 0) {
          queue.push(edge.to);
        }
      }
    });
  }

  if (result.length !== nodes.length) {
    throw new Error("Cycle detected in the graph");
  }

  return result;
}

function drawSubgraph(id) { 
  subEdges = []
  subNodes = []

  let children = getChildren(id) 
  let parents = getParents(id)
  let nodes = [getNode(id)].concat(children).concat(parents)
  var container = document.getElementById("network")
  var options = graphOptions()
  visibleNodes.length = 0
  // for( let i = 0; i < edges.length; i++) {
  //   if( edges[i].from == id || edges[i].to == id) {
  //     visibleNodes.push(edges[i].from)
  //     visibleNodes.push(edges[i].to)
  //   }
  // }
  for(let i = 0; i < nodes.length; i++) {
    visibleNodes.push(nodes[i].id)
  }
  // nodesView.refresh()
  draw(false)
}

function graphOptions() { 
  if (! directedGraphToggleOn) { 
    return {
      nodes: { shape: 'dot', size: 20 },
      edges: {
      smooth: true,
      arrows: { to: true },
    },
    }}
  else { 
    return { 
      autoResize: false, 
      nodes: { shape: 'dot', size: 20 },
      edges: {
        smooth: {
          type: "cubicBezier",
          forceDirection:
            directionInput.value == "UD" || directionInput.value == "DU"
              ? "vertical"
              : "horizontal",
            roundness: 0.5
        },
        arrows: { to: true },
      },
        layout: {
          hierarchical: {
            direction: directionInput.value,
            sortMethod: "directed",
            shakeTowards: "roots"
          },
        }
      }
    }
}

async function updateGraph() {
  const retNodes = await fetch("getNodes",{mode: 'no-cors'})
  const retEdges = await fetch("getEdges",{mode: 'no-cors'})
  nodes = await retNodes.json()
  edges = await retEdges.json()
  draw()
  updateArtifactList()
}


useCasesDropdown.addEventListener("change", () => {
  const h2Title = document.getElementById("title")
  const selectedValue = useCasesDropdown.value;
  h2Title.innerText = `Graph of Use Case ${useCasesDropdown.options[useCasesDropdown.selectedIndex].innerHTML}`
  document.getElementById("artifact-list").innerHTML = ""
  container.innerText = "Updating Graph - this might take a minute"
  sideBarContent.innerHTML = "Select a node to see its detials!!"
  fetch(`useCases/${selectedValue}`).then(response => {
    console.log(`useCases/${selectedValue}`)
    console.log("use case graph has been retrieved")
    console.log(response)
    container.innerText = "Done.  Hang tight while we draw the graph"
    return response.status
  }
  ).then(resp => { 
    console.log("checking response from graph update request")
    console.log(resp)
    console.log("nodes and edges have been updated") 
    if (resp == 200) {
      updateGraph()
    } else {
      container.innerText = resp.toString()
    }
  })
}
)

function updateArtifactList() {
  var artifacts = {}
  for( let i = 0; i < nodes.length; i++) {
      var node = nodes[i]
      var nodeType = node["label"]
      var nodeName = node.name || `${nodeType}-${node.assetId}`
      if ( artifacts[nodeType]) {
          artifacts[nodeType].push(node)
      } else {
          artifacts[nodeType] = [node]
      }
  }
  const artifactList = document.getElementById("artifact-list") 
  const htmlString = []
  for (const k of Object.keys(artifacts)) { 
    htmlString.push(`<li class="list-item">${k}`)
    htmlString.push(`<ul class="nested-list">`)
    for( node of artifacts[k]) {
        const name = node.name || `${node.label}-${node.id}`
        htmlString.push(`<li class="list-item" value=${node.id}>${name}`)
    }
    htmlString.push(`</ul>`)
    htmlString.push(`</li>`)
  }
  const htmlFinalString = htmlString.join(``)
  artifactList.innerHTML = htmlFinalString

  document.querySelectorAll('.list-item').forEach(item => {
    item.addEventListener('click', function (e) {
        const nestedList = this.querySelector('.nested-list');
        if (nestedList && nestedList.contains(e.target)) {
            // If a nested-list item is clicked
            const clickedItem = e.target;
              const nodeId = clickedItem.getAttribute('value');
              activeNodeId = nodeId
              if (nodeId) {
                  // alert(`Value: ${value}`);
                  drawSubgraph(nodeId)
                  let node = getNode(nodeId)
                  const nodeInfo = [];
                  nodeInfo.push(`<strong>Node Details</strong> <br>`)
                  const keys = Object.keys(node)
                  for (let i = 0; i < keys.length; i++) {
                    let k = keys[i]
                    if (k === "url") { 
                      nodeInfo.push(`<strong>${k}</strong><p><a href="${node[k]}">see asset in Datarobot</a> </p> <br>`)
                    } else if (k == "parents") {
                      nodeInfo.push(`<strong>parents</strong><pre id="json">${JSON.stringify(node[k], null, 2)}</pre> <br>`)
                    } else {
                      nodeInfo.push(`<strong>${k}</strong><p>${node[k]}</p> <br>`)
                    }
                  }
                  sideBarContent.innerHTML = nodeInfo.join(``)
                  // sideBarContent.appendChild(emailInput);
                  // sideBarContent.appendChild(shareButton);
                  sideBarContent.appendChild(exportButton)
              }
              
        } else if (nestedList) {
            // If a parent list-item with a nested list is clicked
            e.stopPropagation(); // Prevent event propagation
            nestedList.style.display = nestedList.style.display === 'block' ? 'none' : 'block';
        } else {
            // Leaf node without nested list
            console.log('what did the five fingers say to the face!');
        }
    });
  })
}






const sidebar = document.getElementById("sidebar")
const sideBarContent = document.getElementById("sidebar-content")
// Create a text box (input element)
const emailInput = document.createElement('input');
emailInput.type = 'email'; // Ensure the input is for emails
emailInput.placeholder = 'Enter email'; // Add placeholder text
emailInput.id = 'emailInput'; // Optional: Set an ID for the input

// Create a button
const shareButton = document.createElement('button');
shareButton.textContent = 'Share Node Asset and Parents (not working)'; // Set the button text
// Add an event listener to the button
shareButton.addEventListener('click', () => {
  const email = emailInput.value; // Get the email from the input
  if (email) {
    alert(`Node asset and parents shared with ${email}`); // Replace with your desired action
  } else {
    alert('Please enter a valid email.');
  }
});

// create an export button 

const exportButton = document.createElement("button")
exportButton.textContent = 'Export node, parents, and children'
exportButton.addEventListener("click", function() {

  const tsNodes = topologicalSort(nodes, edges)
  const activeNode = getNode(activeNodeId)
  const parents = getParents(activeNodeId).map( node => node.id) 
  const children = getChildren(activeNodeId).map( node => node.id)
  const exportNodes = tsNodes.filter(val => [activeNodeId].concat(parents).concat(children).includes(val.id))
  // Convert data to JSON string
  const jsonData = JSON.stringify(exportNodes, null, 2);
  // Create a Blob from the data
  const blob = new Blob([jsonData], { type: "application/json" });
  // Create a temporary anchor element
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); // Create a URL for the Blob
  a.download = "data.json"; // Set the file name for download
  // Trigger the download
  a.click();

  // Cleanup the URL object
  URL.revokeObjectURL(a.href);
});


const exportGraphButton = document.getElementById("export-graph")
exportGraphButton.addEventListener("click", function() {
  console.log("export graph button clicked!!")
  const exportNodes = topologicalSort(nodes, edges)
  // Convert data to JSON string
  const jsonData = JSON.stringify(exportNodes, null, 2);
  // Create a Blob from the data
  const blob = new Blob([jsonData], { type: "application/json" });
  // Create a temporary anchor element
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); // Create a URL for the Blob
  a.download = "data.json"; // Set the file name for download
  // Trigger the download
  a.click();

  // Cleanup the URL object
  URL.revokeObjectURL(a.href);
});



;

