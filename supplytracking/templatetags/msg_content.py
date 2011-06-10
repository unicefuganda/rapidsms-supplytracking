from django import template
from django.shortcuts import get_object_or_404
from supplytracking.models import Delivery, DeliveryBackLog
import datetime
from django.db.models import Max


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
    return Delivery.objects.get(transporter=Contact.objects.get(default_connection=connection).name).get_transpoter_msg()

def consignee_poll_msg(connection):
    return Delivery.objects.get(consignee=Contact.objects.get(default_connection=connection).name).get_consignee_msg()    

def send_excel_reminder():
    return Delivery.objects.aggregate(Max('date_uploaded')).get('date_uploaded__max',None) != datetime.datetime.now().date() and \
        DeliveryBackLog.objects.all().exists()
        
def send_excel_reminder_msg():
    return Delivery.objects.aggregate(Max('date_uploaded')).get('date_uploaded__max',None) != datetime.datetime.now().date()


register = template.Library()
register.filter('email_subject', email_subject)
register.filter('excel_reminder_msg', excel_reminder_msg)
register.filter('outstanding_deliveries_msg', outstanding_deliveries_msg)