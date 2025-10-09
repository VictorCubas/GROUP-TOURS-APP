from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class ZonaGeograficaPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response({
            'totalItems': self.page.paginator.count,
            'pageSize': self.get_page_size(self.request),
            'totalPages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
