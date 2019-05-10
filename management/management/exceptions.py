# -*- coding: utf-8 -*-
# import logging

from psycopg2._psycopg import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

# logger = logging.getLogger("django")

# def exception_handler(exc, context):
#     """自定义异常处理"""
#
#     response = drf_exception_handler(exc, context)
#
#     if response is None:
#         view = context['view']
#         if isinstance(exc, DatabaseError):
#             # 数据库异常
#             logger.error('[%s] %s' % (view, exc))
#             response = Response({'msg': 'postgresql_database error'}, status=status.HTTP_507_INSUFFICIENT_STORAGE)
#     else:
#         response.data.clear()
#         response.data['code'] = response.status_code
#         response.data['data'] = []
#
#         if response.status_code == 400:
#             response.data['message'] = 'Bad Request'
#         elif response.status_code == 401:
#             response.data['message'] = 'Unauthorized: lack of jwt token'
#         elif response.status_code == 403:
#             response.data['message'] = 'Forbidden'
#         elif response.status_code == 404:
#             response.data['message'] = 'Not Found'
#         elif response.status_code == 405:
#             response.data['message'] = 'Method Not Allowed'
#         elif response.status_code == 500:
#             response.data['message'] = 'Internal Server Error'
#         elif response.status_code == 503:
#             response.data['message'] = 'Service Unavailable'
#
#     return response
