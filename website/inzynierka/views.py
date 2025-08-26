from django.http import HttpResponse
import datetime


def current_datetime(request):
    now = datetime.datetime.now()
    html = '<html lang="en"><body>It is now <h1>%s</h1>.</body></html>' % now
    return HttpResponse(html)
