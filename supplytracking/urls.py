from django.conf.urls.defaults import *
from supplytracking.views import index,view_deliveries,view_consignees,view_transporters

urlpatterns = patterns('',
 url(r'^$', index, name="supplytracking"),
  url(r'^deliveries$', view_deliveries ),
  url(r'^consignees$', view_consignees ),
  url(r'^transporters$', view_transporters ),
)