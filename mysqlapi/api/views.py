from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import simplejson
from django.conf import settings
from django.db import DatabaseError

from mysqlapi.api.models import DatabaseManager

import subprocess


@csrf_exempt
@require_http_methods(["POST"])
def create(request):
    if not "appname" in request.POST:
        return HttpResponse("App name is missing", status=500)
    appname = request.POST.get("appname", None)
    if not appname:
        return HttpResponse("App name is empty", status=500)
    db = DatabaseManager(appname)
    try:
        db.create()
        db.create_user()
    except DatabaseError, e:
        return HttpResponse(e[1], status=500)
    config = {
        "MYSQL_DATABASE_NAME": db.name,
        "MYSQL_USER": db.username,
        "MYSQL_PASSWORD": db.password,
        "MYSQL_HOST": settings.DATABASES["default"]["HOST"],
        "MYSQL_PORT": db.port,
    }
    return HttpResponse(simplejson.dumps(config), status=201)


@csrf_exempt
@require_http_methods(["DELETE"])
def drop(request, appname):
    db = DatabaseManager(appname)
    try:
        db.drop()
        db.drop_user()
    except DatabaseError, e:
        return HttpResponse(e[1], status=500)
    return HttpResponse("", status=200)


@require_http_methods(["GET"])
def export(request, appname):
    try:
        db = DatabaseManager(appname)
        return HttpResponse(db.export())
    except subprocess.CalledProcessError, e:
        return HttpResponse(e.output.split(":")[-1].strip(), status=500)
