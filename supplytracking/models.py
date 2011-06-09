from django.db import models
from rapidsms.models import Contact
from django.db.models.signals import post_save
from script.models import ScriptProgress,Script
from django.contrib.auth.models import Group
from rapidsms.models import Contact
from script.signals import script_progress_was_completed
from django.utils.text import get_text_list

class Delivery(models.Model):
    SHIPPED='S'
    PENDING='P'
    DELIVERED='D'
    waybill =models.CharField(max_length=20,unique=True)
    consignee=models.ForeignKey(Contact,related_name='consignee',null=True)
    transporter=models.ForeignKey(Contact,blank=True,related_name='transporter',null=True)
    status=models.CharField(max_length=1,choices=(
                                                   (SHIPPED,'shipped'),
                                                   (PENDING, 'pending'),
                                                   (DELIVERED,'delivered'),),default=SHIPPED)
    date_shipped=models.DateField()
    date_uploaded=models.DateTimeField(auto_now=True)
    date_delivered=models.DateField(null=True,blank=True)

    def consignee_msg(self):
        consignee_deliveries=get_text_list(list(Delivery.objects.filter(consignee=self.consignee).values_list('waybill',flat=True)))
        msg="have you received consignments %s"%consignee_deliveries
        return msg
    def get_transporter_msg(self):
        transporter_deliveries=get_text_list(list(Delivery.objects.filter(transporter=self.transporter).values_list('waybill',flat=True)))
        msg="have you received dconsignments %s"%consignee_deliveries
        return msg

    def __unicode__(self):
        return '%s'%self.waybill
class DeliveryBackLog(models.Model):
    delivery=models.ForeignKey(Delivery)

def schedule_deliveries(sender,instance, **kwargs):
    if DeliveryBackLog.objects.all().exists():
        delivery=DeliveryBackLog.objects.order_by(delivery__dateuploaded)[0]
        #delete from backlog
        DeliveryBackLog.objects.get(deliver=delivery).delete()
       
        if delivery.transporter:
            transporter_progress=ScriptProgress.objects.create(script=Script.objects.get(slug="transporter"),
                                              connection=delivery.transporter.default_connection)
        consignee_progress=ScriptProgress.objects.create(script=Script.objects.get(slug="consignee"),
                                              connection=delivery.consignee.default_connection)

        return True

script_progress_was_completed.connect(schedule_deliveries,sender=ScriptProgress)




    