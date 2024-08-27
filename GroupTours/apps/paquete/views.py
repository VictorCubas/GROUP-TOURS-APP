from django.shortcuts import render

# Create your views here.

editado = False
agregado = False
eliminado = False
elimninacion_no_permitida = False
nombre_repetido = False
operacion = None
activo = True
activado = False

def index(request):
    # context = {
    #             'listaPermisos':listaPermiso,
    #             'cantidad_de_resultados': cantidad_de_resultados,
    #             'page': page,
    #             'menu_activo': 'permiso'
    #             }
    
    return render(request, 'paquete.html', )