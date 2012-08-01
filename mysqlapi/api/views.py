# -*- coding: utf-8 -*-
import subprocess

from django.http import HttpResponse
from django.utils import simplejson
from django.views.decorators.http import require_http_methods
from django.views.generic.base import View
from django.shortcuts import get_object_or_404

from mysqlapi import ec2
from mysqlapi.api.models import create_database, DatabaseManager, Instance


def _get_service_host(dict):
    host = dict.get("service_host")
    if not host:
        host = "localhost"
    return host


class CreateUser(View):

    def post(self, request, name, *args, **kwargs):
        if not "hostname" in request.POST:
            return HttpResponse("Hostname is missing", status=500)
        hostname = request.POST.get("hostname", None)
        if not hostname:
            return HttpResponse("Hostname is empty", status=500)
        host = _get_service_host(request.POST)
        db = DatabaseManager(name, host)
        try:
            username, password = db.create_user(name, hostname)
        except Exception, e:
            return HttpResponse(e[1], status=500)
        config = {
            "MYSQL_USER": username,
            "MYSQL_PASSWORD": password,
        }
        return HttpResponse(simplejson.dumps(config), status=201)


class CreateDatabase(View):

    def __init__(self, *args, **kwargs):
        super(CreateDatabase, self).__init__(*args, **kwargs)
        self._client = ec2.Client()

    def post(self, request):
        if not "name" in request.POST:
            return HttpResponse("App name is missing", status=500)
        name = request.POST.get("name", None)
        if not name:
            return HttpResponse("App name is empty", status=500)
        instance = Instance(name=name)
        try:
            create_database(instance, self._client)
        except Exception, e:
            return HttpResponse(e[1], status=500)
        return HttpResponse("ok", status=201)


@require_http_methods(["DELETE"])
def drop_user(request, name, hostname):
    host = _get_service_host(request.GET)
    db = DatabaseManager(name, host)
    try:
        db.drop_user(name, hostname)
    except Exception, e:
        return HttpResponse(e[1], status=500)
    return HttpResponse("", status=200)


class CreateUserOrDropDatabase(View):

    def post(self, request, name, *args, **kwargs):
        return CreateUser.as_view()(request, name)

    def delete(self, request, name, *args, **kwargs):
        return DropDatabase.as_view()(request, name)


class DropDatabase(View):

    def __init__(self, *args, **kwargs):
        super(DropDatabase, self).__init__(*args, **kwargs)
        self._client = ec2.Client()

    def delete(self, request, name, *args, **kwargs):
        try:
            instance = Instance.objects.get(name=name)
        except Instance.DoesNotExist:
            return HttpResponse("Can't drop database 'doesnotexists'; database doesn't exist", status=500)
        self._client.terminate(instance)
        host = _get_service_host(request.GET)
        db = DatabaseManager(name, host)
        try:
            db.drop_database()
        except Exception, e:
            return HttpResponse(e[1], status=500)
        return HttpResponse("", status=200)


@require_http_methods(["GET"])
def export(request, name):
    host = request.GET.get("service_host", "localhost")
    try:
        db = DatabaseManager(name, host)
        return HttpResponse(db.export())
    except subprocess.CalledProcessError, e:
        return HttpResponse(e.output.split(":")[-1].strip(), status=500)


@require_http_methods(["GET"])
def healthcheck(request, name):
    host = _get_service_host(request.GET)
    db = DatabaseManager(name, host)
    status = db.is_up() and 204 or 500
    return HttpResponse(status=status)
