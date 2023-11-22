from django.shortcuts import render

# Create your views here.
# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from django.contrib import messages
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.db.models.functions import Lower, Upper
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from gld import models


def start_registrations(request):
    call_command("start_registrations")
    messages.add_message(request, messages.SUCCESS, "Start registratie voltooid.")
    return redirect(request.META.get("HTTP_REFERER"))
