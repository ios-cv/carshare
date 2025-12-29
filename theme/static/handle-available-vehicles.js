const base_url=document.getElementById("base_url").getAttribute("href");
const available_vehicles_url="http://"+base_url+document.getElementById("available_vehicles_url").getAttribute("href");
const csrftoken=document.querySelector("[name=csrfmiddlewaretoken]").value;
const start_input=document.getElementById("id_reservation_time_0");
const end_input=document.getElementById("id_reservation_time_1");
const available_vehicles_select=document.querySelector("[name=vehicle]");
const selected_vehicle_name=document.getElementById("booking_vehicle_name");
const selected_vehicle_id=document.getElementById("booking_vehicle_id");
const selected_vehicle_registration=document.getElementById("booking_vehicle_registration");
const original_vehicle={
    name:selected_vehicle_name.value,
    id:parseInt(selected_vehicle_id.value),
    registration:selected_vehicle_registration.value
};
const edit_booking_form=document.getElementById("edit_booking_form");
const booking_id=parseInt(document.getElementById("booking_id").value);

const no_options=document.createElement("option");
no_options.textContent=`There are no vehicles available at the selected time`;

const option_unavailable=document.createElement("option");
option_unavailable.textContent=`The vehicle you had is unavailable at the selected time`;
option_unavailable.selected=true;

start_input.setAttribute("type","datetime-local")
start_input.setAttribute("required",true)
end_input.setAttribute("type","datetime-local")
end_input.setAttribute("required",true)
start_input.addEventListener("change",get_available_vehicles);
end_input.addEventListener("change",get_available_vehicles);

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
        if(this.vehicles.length>0){
            //console.log(this.vehicles.find((v)=>v.id=original_vehicle.id))
            if(this.vehicles.find((v)=>v.id==original_vehicle.id)==undefined){
                
                available_vehicles_select.append(option_unavailable);
            }
            this.vehicles.forEach(vehicle => {
                const option=new_option(vehicle);
                if(vehicle.id==original_vehicle.id) option.selected=true;
                available_vehicles_select.append(option);
            });
        }
        else{
            available_vehicles_select.append(no_options);
        }
    }
}

function get_available_vehicles(){
    fetch(available_vehicles_url,
        {
            method:"POST",
            headers:{"X-CSRFToken": csrftoken },
            mode:"same-origin",
            body:JSON.stringify({
                start:start_input.value,
                end:end_input.value,
                booking_id:booking_id,
            })
        })
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

get_available_vehicles();