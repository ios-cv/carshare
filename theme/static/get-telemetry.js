const telemetry_url=document.getElementById("telemetry_url").getAttribute("href");
const csrftoken=document.querySelector("[name=csrfmiddlewaretoken]").value;
const vehicle_id=document.getElementById("vehicle_id").value;
const svgElement=document.getElementById("graph");
const graphMessage=document.getElementById("graph_message")
const telemetry={
    data:[],
    set_data(data){
        this.data=[...data];
        this.update_chart();
    },
    update_chart(){
        const socPoints=this.data.filter((d)=>!(d.soc==null)).map((d)=>{return {y:d.soc,x:d.created_at}}).sort((a,b)=>a.x-b.x);
        drawChart(svgElement,socPoints)
    }
}

function get_telemetry(){
    fetch(telemetry_url,{
        method:"POST",
        headers:{"X-CSRFToken":csrftoken},
        mode:"same-origin",
        body:JSON.stringify({
            "vehicle_id":vehicle_id
        })
    })
    .then((response)=>{
        if(!response.ok){
            throw new Error(`Http response error:${response.status} - ${response.statusText}`)
        }
        return response.json();
    })
    .then((data)=>{
        if(data){
            telemetry.set_data(data);
        }
    })
}

get_telemetry();

function drawChart(svgElement, points) {
    if (!svgElement || !Array.isArray(points) || points.length <= 1) {
        graphMessage.textContent="Not enough telemetry recieved to draw graph."
        return;
    }
    graphMessage.textContent="";

    // Determine min and max values for scaling
    const minX = Math.min(...points.map(p => p.x));
    const maxX = Math.max(...points.map(p => p.x));
    
    const minY = 0//Math.min(...points.map(p => p.y));
    const maxY = 100;

    const padding = (maxY-minY)/8;

    // Compute chart dimensions
    const chartHeight = maxY - minY + 4 * padding;
    const chartWidth = 1.61*chartHeight;
    

    // Convert points to chart coordinates
    const scaleX = (chartWidth - 2 * padding) / (maxX - minX);
    const scaleY = (chartHeight - 4 * padding) / (maxY - minY);
    function transformPoint(p) {
        return {
            x: (p.x - minX) * scaleX,
            y: (p.y - minY) * scaleY
        };
    }

    function reverseTransform(p){
        return {
            x: (p.x / scaleX) +minX,
            y: -(p.y / scaleY) +minY,
        };
    }

    const transformedPoints=points.map((p)=>transformPoint(p));
    const minTX = Math.min(...transformedPoints.map(p => p.x));
    const maxTX = Math.max(...transformedPoints.map(p => p.x));
    const minTY = 0;
    const maxTY = 100;

    svgElement.setAttribute("viewBox", `${minTX-padding-20} -${maxTY+padding} ${chartWidth+2*padding+20} ${chartHeight+2*padding}`);
    svgElement.setAttribute("preserveAspectRatio", "xMidYMid meet");
    
    // Calculate appropriate circle radius and stroke width based on scale
    const scaleFactor = (chartWidth + chartHeight) / 300;
    const circleRadius = scaleFactor;
    const strokeWidth = scaleFactor / 2;

    // Create grid lines
    const gridHeight=maxTY;
    const gridWidth=maxTX-minTX;
    const gridSpacingY = gridHeight/10;
    const gridSpacingX = gridWidth/10;
    const gridGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    gridGroup.setAttribute("stroke", "lightgray");
    gridGroup.setAttribute("stroke-width", strokeWidth/1.2);

    // Vertical grid lines
    for (let x = minTX; x <= maxTX+0.5*gridSpacingX; x += gridSpacingX) {
        const gridLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
        gridLine.setAttribute("x1", x);
        gridLine.setAttribute("y1", 0);
        gridLine.setAttribute("x2", x);
        gridLine.setAttribute("y2", -maxTY);
        gridGroup.appendChild(gridLine);
    }

    // X Axis Labels
    const timeRange=maxX-minX;
    const timeStep=timeRange/10;
    for(let step=1;step<4;step++){
        const stepDateTime=new Date((minX+step*(2*timeStep)+timeStep)*1000);
        const xStep=document.createElementNS("http://www.w3.org/2000/svg", "text");
        xStep.setAttribute("x", minTX + gridWidth/5 * step );
        xStep.setAttribute("y", 0 + padding);
        xStep.setAttribute("font-size", scaleFactor*2.8);
        xStep.textContent=`${stepDateTime.toDateString()} ${stepDateTime.toLocaleTimeString()}`;
        svgElement.appendChild(xStep);
        const gridDash = document.createElementNS("http://www.w3.org/2000/svg", "line");
        gridDash.setAttribute("x1", minTX + gridWidth/5 * step + gridWidth/10);
        gridDash.setAttribute("y1", 0);
        gridDash.setAttribute("x2", minTX + gridWidth/5 * step + gridWidth/10);
        gridDash.setAttribute("y2", 0 + padding /2);
        gridGroup.appendChild(gridDash);
    }

    const startDateTime=new Date(minX*1000);
    const xStart=document.createElementNS("http://www.w3.org/2000/svg", "text");
    xStart.setAttribute("x", minTX);
    xStart.setAttribute("y", 0 + padding);
    xStart.setAttribute("font-size", scaleFactor*2.8);
    xStart.textContent=`${startDateTime.toDateString()} ${startDateTime.toLocaleTimeString()}`;
    svgElement.appendChild(xStart);
    const gridStartDash = document.createElementNS("http://www.w3.org/2000/svg", "line");
    gridStartDash.setAttribute("x1", minTX);
    gridStartDash.setAttribute("y1", 0);
    gridStartDash.setAttribute("x2", minTX);
    gridStartDash.setAttribute("y2", 0 + padding /2);
    gridGroup.appendChild(gridStartDash);

    const endDateTime=new Date(maxX*1000);
    const xEnd=document.createElementNS("http://www.w3.org/2000/svg", "text");
    xEnd.setAttribute("x", maxTX );
    xEnd.setAttribute("y", 0 + padding);
    xEnd.setAttribute("font-size", scaleFactor*2.8);
    xEnd.textContent=`${endDateTime.toDateString()} ${endDateTime.toLocaleTimeString()}`;
    svgElement.appendChild(xEnd);
    const gridEndDash = document.createElementNS("http://www.w3.org/2000/svg", "line");
    gridEndDash.setAttribute("x1", maxTX);
    gridEndDash.setAttribute("y1", 0);
    gridEndDash.setAttribute("x2", maxTX);
    gridEndDash.setAttribute("y2", 0 + padding /2);
    gridGroup.appendChild(gridEndDash);

    // y Axis Label
    const yAxisLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
    yAxisLabel.setAttribute("x", -20);
    yAxisLabel.setAttribute("y", -chartHeight/6);
    yAxisLabel.setAttribute("font-size", scaleFactor*5);
    yAxisLabel.setAttribute("transform", `rotate(-90 -20 -${chartHeight/6})`);
    yAxisLabel.setAttribute("stroke","None");
    yAxisLabel.textContent="Charge Percentage";
    gridGroup.appendChild(yAxisLabel);

    //Horizontal grid lines
    for (let y = -1*maxTY; y <= 0; y += gridSpacingY) {
        const gridLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
        gridLine.setAttribute("x1", minTX);
        gridLine.setAttribute("y1", y);
        gridLine.setAttribute("x2", maxTX);
        gridLine.setAttribute("y2", y);
        gridGroup.appendChild(gridLine);

        // Y Axis Labels
        const textElement = document.createElementNS("http://www.w3.org/2000/svg", "text");
        textElement.setAttribute("x", minTX-padding);
        textElement.setAttribute("y", y+strokeWidth*5);
        textElement.setAttribute("font-size", scaleFactor*3);
        textElement.setAttribute("stroke","None");
        textElement.textContent = Math.round(reverseTransform({x:0,y:y}).y)+"%";
        gridGroup.appendChild(textElement);
    }
    svgElement.appendChild(gridGroup);
    const xEndBBox=xEnd.getBBox();
    xEnd.setAttribute("x",maxTX-xEndBBox.width);

    // Create a polyline element
    const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    
    // Convert points array to a string for the polyline 'points' attribute
    const pointsString = points.map(p => {
        const transformed = transformPoint(p);
        return `${transformed.x},${-transformed.y}`;
    }).join(" ");
    polyline.setAttribute("points", pointsString);
    polyline.setAttribute("stroke", "#9999cc");
    polyline.setAttribute("fill", "none");
    polyline.setAttribute("stroke-width", strokeWidth);

    // Append polyline to the SVG element
    svgElement.appendChild(polyline);
    
    // Draw individual points with scaled radius
    points.forEach(point => {
        const transformed = transformPoint(point);
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", transformed.x);
        circle.setAttribute("cy", -transformed.y);
        circle.setAttribute("r", circleRadius);
        circle.setAttribute("fill", "#44aaff");
        circle.addEventListener("mouseenter",()=>{
            circle.setAttribute("r", circleRadius*2);
            const date=new Date(point.x*1000)
            const bubble=drawSpeechBubble(svgElement,transformed.x,-transformed.y,`${point.y}% @ ${date.toDateString()} ${date.toLocaleTimeString()}`,circle,scaleFactor)
            circle.addEventListener("mouseleave",()=>{
                bubble.remove();    
                circle.setAttribute("r", circleRadius);
            });
        })
        svgElement.appendChild(circle);
    });
}

function drawSpeechBubble(svgElement, x, y, text, before,scaleFactor=10) {
    const padding = scaleFactor*5;
    const fontSize = scaleFactor*3;
    
    // Create text element to measure size
    const textElement = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textElement.setAttribute("x", x);
    textElement.setAttribute("y", y);
    textElement.setAttribute("font-size", fontSize);
    textElement.setAttribute("visibility", "hidden");
    textElement.textContent = text;
    svgElement.appendChild(textElement);
    
    // Get bounding box size
    const bbox = textElement.getBBox();
    const width = bbox.width + 2 * padding;
    const height = bbox.height + 2 * padding;
    
    // Determine bubble position
    const svgBox = svgElement.viewBox.baseVal;
    let bubbleX = Math.min(Math.max(x - width / 2, svgBox.x), svgBox.x + svgBox.width - width);
    let bubbleY = Math.min(Math.max(y - height - 10, svgBox.y), svgBox.y + svgBox.height - height);
    
    // Create speech bubble rect
    const bubble = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bubble.setAttribute("x", bubbleX);
    bubble.setAttribute("y", bubbleY);
    bubble.setAttribute("width", width);
    bubble.setAttribute("height", height);
    bubble.setAttribute("rx", 10);
    bubble.setAttribute("ry", 10);
    bubble.setAttribute("fill", "white");
    bubble.setAttribute("stroke", "black");
    bubble.setAttribute("stroke-width", 0.1);
    
    // Create speech bubble pointer
    const pointer = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
    const pointerPoints = [
        `${x},${y}`,
        `${bubbleX + width / 2 - 5},${bubbleY + height}`,
        `${bubbleX + width / 2 + 5},${bubbleY + height}`
    ].join(" ");
    pointer.setAttribute("points", pointerPoints);
    pointer.setAttribute("fill", "white");
    pointer.setAttribute("stroke", "black");
    pointer.setAttribute("stroke-width", 0.1);
    
    // Update text position
    textElement.setAttribute("x", bubbleX + padding);
    textElement.setAttribute("y", bubbleY + height / 2 + fontSize / 2-padding/4);
    textElement.setAttribute("visibility", "visible");

    
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    
    group.appendChild(pointer);
    group.appendChild(bubble);
    group.appendChild(textElement);
    // Append elements
    before.remove();
    svgElement.appendChild(group);
    svgElement.appendChild(before);
    return group;
}
