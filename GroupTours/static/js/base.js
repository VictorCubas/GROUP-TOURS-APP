const toggler = document.querySelector(".btn");
toggler.addEventListener("click",function(){
    document.querySelector("#sidebar").classList.toggle("collapsed");
});


 // RESALTAR ITEM ACTIVO EN EL SIDEBAR
const menuActivo = document.getElementById("menu-activo");
console.log('menuActivo: ', menuActivo.value);
if(menuActivo){
    const menuActivoNav = `menu-${menuActivo.value}`;
    let itemActive =  document.getElementById(menuActivoNav);

    itemActive.classList.add("activo");
    console.log('itemActive: ', itemActive);
    

    let parentElement = itemActive.parentElement;
    while (parentElement && !parentElement.classList.contains('sidebar-dropdown')) {
        parentElement = parentElement.parentElement;
    }

    if (parentElement) {
        parentElement.classList.add("show");
        console.log('parentElement: ', parentElement);
    }

}

var itemActivo = null;
const menuItems = document.querySelectorAll(".item-menu");
menuItems.forEach(function (opcion) {
    opcion.addEventListener("click", function (event) {
        if(itemActivo && itemActivo !== opcion){
            
            itemActivo.classList.remove('activo');
        }

        itemActivo = opcion;
        opcion.classList.add("activo");
    });
});



//Boostrap select
 $('.selectpicker').selectpicker();


//  window.onload = function() { dispararModalEliminacionExitosa(); };

//SWEET ALER, ELMINACION EXITOSA
function dispararModalEliminacionExitosa(){
    console.log('andrea.....')
    eliminacionExitosaEl = document.getElementById('eliminacionExitosa');
    console.log('eliminacionExitosaEl: ', eliminacionExitosaEl);
    console.log('eliminacionExitosaEl.value 1: ', eliminacionExitosaEl.value);

    if(eliminacionExitosaEl.value === 'True'){
        Swal.fire({
            title: "Desactivado!",
            text: "Se ha realizado la desactivación.",
            icon: "success"
            });
    }
    else if(eliminacionExitosaEl.value === 'False'){
        Swal.fire({
        icon: "error",
        title: "Oops...",
        text: "¡Algo salio! Vuelva a intentarlo",
        });
    }
    else if(eliminacionExitosaEl.value === 'warning'){
        Swal.fire({
        icon: "warning",
        title: "Oops...",
        text: "¡Permiso en uso! No se puede desactivar.",
        });
    }
}



window.onload = function() { dispararModalActivacionExitosa(); dispararModalEliminacionExitosa(); };

function dispararModalActivacionExitosa(){
    activacionExitosaEl = document.getElementById('activacionExitosa');
    console.log('activacionExitosaEl.value 2: ', activacionExitosaEl.value);

    if(activacionExitosaEl.value === 'True'){
        Swal.fire({
            title: "Activado!",
            text: "Se ha realizado la activación.",
            icon: "success"
            });
    }
    else if(activacionExitosaEl.value === 'False'){
        Swal.fire({
        icon: "error",
        title: "Oops...",
        text: "¡Algo salio! Vuelva a intentarlo",
        });
    }
}



// EVENTO PARA DETECTAR CADA VEZ QUE SE QUIERA ELIMINAR
// (function () {

//     const btnEliminacion = document.querySelectorAll(".btnEliminacion");

//     btnEliminacion.forEach(btn => {
//         btn.addEventListener('click', (e) => {
//             const enlace = document.getElementById('enlace-eliminacion');
//             console.log('enlace.href: ', enlace.href);
//             // this.confirmarElimnacion(enlace.href)
//             e.preventDefault();
            
//         });
//     });
    
// })();


function eliminar(url, id){
    const urlFin = window.location.origin + '/' + url + '/' + id;
    confirmarElimnacion(urlFin);
}


function confirmarElimnacion(url){
    console.log('confirmarElimnacion: ', url);
    let operacion = 'activar';
    let confirmButtonText = 'Sí, activarlo!';

    if(url.includes('eliminar')){
        operacion = 'desactivar';
        confirmButtonText = 'Sí, desactivarlo!';
    }


    Swal.fire({
        title: `Estás seguro de que quieres ${operacion}?`,
        // text: "No se podrá revertir la acción!",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: confirmButtonText
      }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = url;
            console.log('url: ', url);
        }
      });
}

// const opcionTodos = document.getElementById('opcion_todos');
// console.log(opcionTodos)
const selectpicker = document.querySelector('.selectpicker');

var valorAnterior = null

selectpicker.addEventListener('change', function(event) {
        const selectedOption = event.target.value;
        if (selectedOption === '*') {
            // Desmarcar todas las opciones excepto la opción "Marcar todos"
            let options = selectpicker.querySelectorAll('.options-permisos');
            options.forEach(option => {
                console.log('options: ', options)
                // option.removeAttribute('selected'); // Cambiar selected a false
            });
        }

        valorAnterior = event.target.value
    });
//     valorAnterior = event.target.value
// });
