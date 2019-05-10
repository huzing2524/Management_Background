# -*- coding: utf-8 -*-
import jwt
from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from rest_framework import status


class MyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # print(request.path)
        if request.path in ["/bg/login/", "/bg/login"]:
            return None
        else:
            token = request.META.get("HTTP_AUTHORIZATION")
            if token:
                try:
                    token = token.split(" ")[-1]
                    # print(token)
                    payload = jwt.decode(token, settings.SECRET_KEY)
                    if "username" in payload and "exp" in payload:
                        # print("payload=", payload)
                        return None
                    else:
                        raise jwt.InvalidTokenError
                except jwt.ExpiredSignatureError:
                    return HttpResponse("jwt token expired", status=status.HTTP_401_UNAUTHORIZED)
                except jwt.InvalidTokenError:
                    return HttpResponse("Invalid jwt token", status=status.HTTP_401_UNAUTHORIZED)
            else:
                return HttpResponse("lack of jwt token", status=status.HTTP_401_UNAUTHORIZED)

    def process_response(self, request, response):
        return response
