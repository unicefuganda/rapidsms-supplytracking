import rapidsms
import datetime

from rapidsms.apps.base import AppBase
from .models import *
import re
from supplytracking.models import *
from script.models import ScriptProgress
from script.utils.incoming import incoming_progress
from django.core.mail import send_mail

class App (AppBase):

    def handle (self, message):
        reg = re.compile('COMPLETE|DAMAGED')
        waybills = filter(None, reg.split(message.db_message.text.upper()))
        if len(waybills) > 0:
            for waybill in waybills:   
#            waybill=waybill_match.group('waybill')
                delivery=Delivery.objects.get(waybill=waybill.strip())
                
                #check if message is from consignee
                if delivery.consignee.default_connection.identity == message.connection.identity:
                    delivery.status = Delivery.DELIVERED
                    delivery.date_delivered = datetime.datetime.now()
                    delivery.save()
                    
                    #if it is in the backlog, delete it
                    if DeliveryBackLog.objects.filter(delivery__waybill=waybill).exists():
                        DeliveryBackLog.objects.get(delivery=delivery).delete()
                    
            #in case consignee has sent delivery report, send it out to supply admins        
            if delivery.consignee.default_connection.identity == message.connection.identity:
                supply_admins = Contact.objects.filter(groups__name__in=['supply_admin'])
                recipients = list(supply_admins.values_list('user__email',flat=True).distinct())
                sender = 'no-reply@uganda.rapidsms.org'
                subject = 'SupplyTracking: Delivery Report'
                message = message.db_message.text
                if message.strip():
                    send_mail(subject, message, sender, recipients, fail_silently=False)  
            
            #process and send out response to message sender
            response = incoming_progress(message)
            if response:
                message.respond(response)
            return True      
        else:
            return False


