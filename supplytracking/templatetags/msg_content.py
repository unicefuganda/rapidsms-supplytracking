from django import template
from django.shortcuts import get_object_or_404
from supplytracking.models import Delivery, DeliveryBackLog
from script.models import ScriptProgress
import datetime
from django.db.models import Max
from rapidsms.models import Contact, Connection


def email_subject(connection):
    if send_excel_reminder():
       return 'Reminder to Upload Consignments Excel Sheet'
    else:
        return 'Outstanding Deliveries Report'

def excel_reminder_msg(connection):
    if send_excel_reminder_msg():
        return 'You are kindly  reminded to upload the Excel Sheet from UNITRAC containing all outgoing consignments!' \
        '<p>Please login <a href="#">here</a> to upload the excel sheet</p>'
    else:
        return None

def outstanding_deliveries_msg(connection):
    if len(DeliveryBackLog.objects.all())>0:
        deliveries = []
        for d in DeliveryBackLog.objects.all():
            deliveries.append(d.waybill)
        list = '<br />'.join(deliveries) 
        return 'The following Deliveries are outstanding' \
                '<p>'+list+'</p>'
                
def transporter_poll_msg(connection):
    transporter_name = Contact.objects.get(connection=Connection.objects.get(pk=connection).identity).name
    return Delivery.objects.filter(transporter=transporter_name)[0].get_transporter_msg()

def consignee_poll_msg(connection):
    return Delivery.objects.filter(consignee=Contact.objects.get(connection=connection).name)[0].get_consignee_msg()    

def send_excel_reminder():
    return Delivery.objects.aggregate(Max('date_uploaded')).get('date_uploaded_max') != datetime.datetime.now().date() and \
        len(DeliveryBackLog.objects.all()) == 0
        
def send_excel_reminder_msg():
    return Delivery.objects.aggregate(Max('date_uploaded')).get('date_uploaded_max') != datetime.datetime.now().date()


register = template.Library()
register.filter('email_subject', email_subject)
register.filter('excel_reminder_msg', excel_reminder_msg)
register.filter('outstanding_deliveries_msg', outstanding_deliveries_msg)
register.filter('transporter_poll_msg', transporter_poll_msg)
register.filter('consignee_poll_msg', consignee_poll_msg)