const base_url=document.getElementById("base_url").getAttribute("href");
const csrftoken=document.querySelector("[name=csrfmiddlewaretoken]").value;
const start_input=document.getElementById("id_reservation_time_0");
const end_input=document.getElementById("id_reservation_time_1");
const available_vehicles_select=document.querySelector("[name=vehicle]");
const selectedOption = available_vehicles_select.options[available_vehicles_select.selectedIndex];
const original_vehicle = parseVehicleInfo(selectedOption.textContent);
const template_available_vehicles_url="http://"+base_url+document.getElementById("available_vehicles_url").getAttribute("href");
const edit_booking_form=document.getElementById("edit_booking_form");

const available_vehicles={
    vehicles:[],
    setVehicles(vehicles_list){
        this.vehicles=[...vehicles_list];
        this.update_UI();
    },
    update_UI(){
        while(available_vehicles_select.firstChild){
            available_vehicles_select.removeChild(available_vehicles_select.firstChild);
        }
        const original_selection=new_option(original_vehicle);
        original_selection.selected=true;
        available_vehicles_select.append(original_selection);
        this.vehicles.forEach(vehicle => {
            if(vehicle.id!=original_vehicle.id) available_vehicles_select.append(new_option(vehicle));
        });
    }
}

function get_available_vehicles(){
        let available_vehicles_url=template_available_vehicles_url.replace("start",start_input.value);
        available_vehicles_url=available_vehicles_url.replace("end",end_input.value);
        fetch(available_vehicles_url,{method:"GET",headers:{"X-CSRFToken": csrftoken },mode:"same-origin"})
        .then((response) => {
            if(!response.ok){
                throw new Error(`Http response error:${response.status} - ${response.statusText}`)
            }
            return response.json();
        })
        .then((data)=>{
            if(data){
                available_vehicles.setVehicles(data);
            }
            else{
                available_vehicles.setVehicles([]);
            }
        })
        .catch((error)=>{
            console.log(`Error fetching available vehicles:${error}`)
            available_vehicles.setVehicles([]);
        })
    }

function new_option(v){
    const option=document.createElement("option");
    option.value=v.id;
    option.textContent=`${v.name} (${v.registration})`;
    return option
}
start_input.addEventListener("change",get_available_vehicles);
end_input.addEventListener("change",get_available_vehicles);
get_available_vehicles();

function parseVehicleInfo(input) {
    // Regular expression to capture the name, registration, and id
    const regex = /^([^-]+) - ([^\[]+) \[(\d+)\]$/;
    
    const match = input.match(regex);
    if (match) {
        return {
        name: match[1].trim(),         // Capture the name part
        registration: match[2].trim(), // Capture the registration part
        id: match[3]         // Capture the ID and convert it to an integer
        };
    } else {
        throw new Error('Invalid input format');
    }
}