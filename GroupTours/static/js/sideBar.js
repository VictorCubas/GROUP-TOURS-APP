const toggler = document.querySelector(".btn");
toggler.addEventListener("click",function(){
    document.querySelector("#sidebar").classList.toggle("collapsed");
});


 // Resaltar ítem activo
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


 //SWEET ALER, ELMINACION EXITOSA
 window.onload = function() { dispararModalEliminacionExitosa(); };

function dispararModalEliminacionExitosa(){
    eliminacionExitosaEl = document.getElementById('eliminacionExitosa');
    console.log('eliminacionExitosaEl.value: ', eliminacionExitosaEl.value);

    if(eliminacionExitosaEl.value === 'True'){
        Swal.fire({
            title: "Eliminado!",
            text: "Se ha realizado la eliminación.",
            icon: "success"
            });
    }
}

//EVENTO PARA DETECTAR CADA VEZ QUE SE QUIERA ELIMINAR
(function () {

    const btnEliminacion = document.querySelectorAll(".btnEliminacion");

    btnEliminacion.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const enlace = document.getElementById('enlace-eliminacion');
            this.confirmarElimnacion(enlace.href)
            e.preventDefault();
            
        });
    });
    
})();


function confirmarElimnacion(url){
    Swal.fire({
        title: "Estás seguro de que quieres eliminar?",
        text: "No se podrá revertir la acción!",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: "Sí, elimnalo!"
      }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = url;
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
