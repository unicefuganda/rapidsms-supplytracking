from django.conf.urls.defaults import *
from supplytracking.views import index,view_deliveries,view_consignees,view_transporters

urlpatterns = patterns('',
 url(r'^supply_tracking/$', index ,name="supply_tracking"),
  url(r'^supply_tracking/deliveries$', view_deliveries ),
  url(r'^supply_tracking/consignees$', view_consignees ),
  url(r'^supply_tracking/transporters$', view_transporters ),
)