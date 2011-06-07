from django.db import models
from rapidsms.models import Contact
from django.db.models.signals import post_save
from script.models import ScriptProgress,Script
from django.contrib.auth.models import Group
from rapidsms.models import Contact


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
                                                   (DELIVERED,'delivered'),))
    date_shipped=models.DateField()
    date_delivered=models.DateField(null=True,blank=True)

    def __unicode__(self):
        return '%s'%self.waybill

def script_creation_handler(sender,instance, **kwargs):
    #create script progress for admins , transporters  and consignees
    #instance = kwargs['instance']
    supply_admins=Contact.objects.filter(groups=Group.objects.filter(name="supply_admins"))
    for admin in supply_admins:
        scriptprogress,progress_created=ScriptProgress.objects.get_or_create(script=Script.objects.get(slug="hq_supply_staff"),
                                              connection=admin.connection)
        scriptprogress.start()
    if instance.transporter:
        transporter_progress=ScriptProgress.objects.create(script=Script.objects.get(slug="transporter"),
                                          connection=instance.transporter.default_connection)
        transporter_progress.start()
    consignee_progress=ScriptProgress.objects.create(script=Script.objects.get(slug="consignee"),
                                          connection=instance.consignee.default_connection)
    consignee_progress.start()

    return True

#post_save.connect(script_creation_handler,sender=Delivery)




    