# apps/arqueo_caja/pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPageNumberPagination(PageNumberPagination):
    """
    Paginación personalizada que retorna metadatos adicionales:
    - pageSize: tamaño de página
    - previous: página anterior (null si no existe)
    - next: página siguiente (null si no existe)
    - totalItems: cantidad total de items
    - totalPages: cantidad total de páginas
    - currentPage: página actual
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'pageSize': self.page_size,
            'currentPage': self.page.number,
            'previous': self.get_previous_link(),
            'next': self.get_next_link(),
            'totalItems': self.page.paginator.count,
            'totalPages': self.page.paginator.num_pages,
        })
