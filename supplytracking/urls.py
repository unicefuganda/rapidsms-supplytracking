from django.conf.urls.defaults import *
from supplytracking.views import index

urlpatterns = patterns('',
 url(r'^supply_tracking$', index ,name="supply_tracking"),
)