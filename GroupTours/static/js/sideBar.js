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