from django import template
from django.shortcuts import get_object_or_404
from supplytracking.models import Delivery, DeliveryBackLog
from script.models import ScriptStep, ScriptProgress
import datetime
import itertools
from django.db.models import Max
from rapidsms.models import Contact, Connection

register = template.Library()

@register.filter
def email_subject(connection):
    if send_excel_reminder():
       return 'Reminder to Upload Consignments Excel Sheet'
    else:
        return 'Outstanding Deliveries Report'

@register.filter
def excel_reminder_msg(connection):
    if send_excel_reminder_msg():
        return 'You are kindly  reminded to upload the Excel Sheet from UNITRAC containing all outgoing consignments!\r\n' \
        'Please login at the supply tracking administration page to upload the excel sheet'
    else:
        return ''

@register.filter
def outstanding_deliveries_msg(connection):
    outdated = []
    for dl in Delivery.objects.filter(status=Delivery.SHIPPED):
        if dl.overdue:
            outdated.append(dl)
    if len(DeliveryBackLog.objects.all())>0 or len(outdated)>0:
        backlogs = DeliveryBackLog.objects.all()
        deliveries = []
        for outdated_d in outdated:
            deliveries.append(outdated_d.waybill)
            
        for backlog_d in backlogs:
            deliveries.append(backlog_d.delivery.waybill)
            
        listx = '\n'.join(list(set(deliveries))) 
        return '\n\nThe following Deliveries are outstanding\n' \
                +listx+'\r'
    else:
        return ''

@register.filter                
def transporter_poll_msg(connection):
    return Delivery.objects.filter(transporter=Connection.objects.get(pk=connection.pk).contact)[0].get_transporter_msg()

@register.filter
def consignee_poll_msg(connection):
    return Delivery.objects.filter(consignee=Connection.objects.get(pk=connection.pk).contact)[0].get_consignee_msg()    

def send_excel_reminder():
    return Delivery.objects.aggregate(Max('date_uploaded')).get('date_uploaded__max',None) != datetime.datetime.now() and not \
        DeliveryBackLog.objects.all().exists()
        
def send_excel_reminder_msg():
    return Delivery.objects.aggregate(Max('date_uploaded')).get('date_uploaded__max',None) != datetime.datetime.now()