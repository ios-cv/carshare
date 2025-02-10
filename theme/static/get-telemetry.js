const base_url=document.getElementById("base_url").getAttribute("href");
const telemetry_url="http://"+base_url+document.getElementById("telemetry_url").getAttribute("href");
const csrftoken=document.querySelector("[name=csrfmiddlewaretoken]").value;
const vehicle_id=document.getElementById("vehicle_id").value;

const telemetry={
    data:[],
    set_data:(data)=>{
        this.data.push(...data);
    }
}

function getTelemetry(){
    console.log(`getting telemetry from ${telemetry_url}`);
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
        console.log(data);
        if(data){
            telemetry.set_data(data);
        }
    })
}

console.log("this ran");
getTelemetry();