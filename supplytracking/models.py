from django.db import models
from rapidsms.models import Contact
from django.db.models.signals import post_save
from supplytracking.utils import script_creation_handler

class Delivery(models.Model):
    waybill =models.CharField(max_length=20,unique=True)
    consignee=models.ForeignKey(Contact,related_name='consignee',null=True)
    transporter=models.ForeignKey(Contact,blank=True,related_name='transporter',null=True)
    status=models.CharField(max_length=22,choices=(('shipped','shipped'),('delivered','delivered'),))
    date_shipped=models.DateField()
    date_delivered=models.DateField(null=True,blank=True)

    def __unicode__(self):
        return '%s'%self.waybill

post_save.connect(script_creation_handler,sender=Delivery)




    