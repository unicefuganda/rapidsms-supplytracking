import rapidsms
import datetime

from rapidsms.apps.base import AppBase
from .models import *
import re
from supplytracking.models import *
from script.models import ScriptProgress
from script.utils.incoming import incoming_progress

class App (AppBase):

    def handle (self, message):
        waybill_reg=re.compile(r'(?P<waybill>([a-zA-Z]{2,2})/([a-zA-Z]{2,2})([0-9]{2,2})/([0-9]{5,5}))')
        waybill_match=waybill_reg.search(message.db_message.text)
        if waybill_match:
            waybill=waybill_match.group('waybill')
            delivery=Delivery.objects.get(waybill=waybill)
            
            #check if message is from consignee
            if delivery.consignee.default_connection.identity==message.connection.identity:
                delivery.status=Delivery.DELIVERED
                delivery.save()
                
                #if it is in the backlog, delete it
                if DeliveryBackLog.objects.filter(delivery__waybill=waybill).exists():
                    DeliveryBackLog.objects.get(delivery=delivery).delete()
                
                #get the response to the message if any and send it out
                response = incoming_progress(message)
                if response:
                    message.respond(response)
                return True
            
            #if message is from the transporter simply process the response and send it to transporter
            elif delivery.transporter.default_connection.identity == message.connection.identity:
                response = incoming_progress(message)
                if response:
                    message.respond(response)
                return True                     
        else:
            return False


