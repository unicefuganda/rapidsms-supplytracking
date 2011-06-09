import rapidsms
import datetime

from rapidsms.apps.base import AppBase
from .models import *
import re
from supplytracking.models import *
from script.models import ScriptProgress

class App (AppBase):

    def handle (self, message):
            waybill_reg=re.compile(r'(?P<waybill>([a-zA-Z]{2,2})/([a-zA-Z]{2,2})([0-9]{2,2})/([0-9]{5,5}))')
            waybill_match=waybill_reg.search(message.db_message)
            if waybill_match:
                waybill=waybill_match.group('waybill')
                delivery=Delivery.objects.get(waybill=waybill)
                if  DeliveryBackLog.objects.filter(delivery__waybill=waybill).exists():
                    delivery.status=Delivery.delivered_status
                    delivery.save()
                elif delivery.consignee.default_connection==message.connection and ScriptSession.objects.filter(connection=message.connection).exists():
                    if ScriptProgress.objects.get(connection=message.connection).status:
                        delivery.status=Delivery.delivered_status
                        delivery.save()
                        
            return True


