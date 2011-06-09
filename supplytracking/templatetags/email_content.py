from django import template
from django.shortcuts import get_object_or_404
from supplyTracking import Delivery, DeliveryBackLog
import datetime


def email_subject(connection):
    if len(DeliveryBackLog.objects.all()) > 0 or \
    (len(DeliveryBackLog.objects.all()) > 0 and \
     (Delivery.objects.aggregate(Max('date_uploaded')) + timedelta(days=3) <= datetime.datetime)):
       return 'SupplyTracking: Reminder to Upload Consignments Excel Sheet'
    else:
        return 'SupplyTracking: Outstanding Deliveries Report'

def excel_reminder(connection):
    return 'You are minded to upload excel sheet!'

def outstanding_deliveries(connection):
    return 'The following are the outstanding Deliveries'


register = template.Library()
register.filter('email_subject', email_subject)
register.filter('excel_reminder', excel_reminder)
register.filter('outstanding_deliveries', outstanding_deliveries)