from django import template
from django.shortcuts import get_object_or_404
from supplytracking.models import Delivery, DeliveryBackLog
import datetime


def email_subject(connection):
    if send_excel_reminder:
       return 'Reminder to Upload Consignments Excel Sheet'
    else:
        return 'Outstanding Deliveries Report'

def excel_reminder_msg(connection):
    if send_excel_reminder:
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

def send_excel_reminder():
    return len(DeliveryBackLog.objects.all()) > 0 or \
    (len(DeliveryBackLog.objects.all()) > 0 and \
     (Delivery.objects.aggregate(Max('date_uploaded')) + timedelta(days=3) <= datetime.datetime))


register = template.Library()
register.filter('email_subject', email_subject)
register.filter('excel_reminder_msg', excel_reminder_msg)
register.filter('outstanding_deliveries_msg', outstanding_deliveries_msg)