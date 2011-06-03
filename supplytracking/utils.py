from script.models import *
from status160.models import Team
from supplytracking.models import *
from django.contrib.auth.models import User
from django.conf import settings

def create_scripts():
    

    site = Site.objects.get_or_create(pk=settings.SITE_ID, defaults={
            'domain':'example.com',
        })
    admin_script = Script.objects.create(slug="hq_supply_staff",name="supply staff script")
    admin_script.sites.add(Site.objects.get_current())
    reminder_email=Email.objects.create(subject="SupplyTracking: Excel Upload reminder" ,message="You are reminded to upload the deliveries excel script")
    admin_script.steps.add(ScriptStep.objects.create(
        script=admin_script,
        email=reminder_email,
        order=0,
        rule=ScriptStep.RESEND_MOVEON,
        start_offset=0,
        retry_offset=3600*24,
        num_tries=100,
        ))
    reminder_email=Email.objects.create(subject="SupplyTracking: Excel Upload reminder" ,message="you have "+str(Delivery.objects.filter(status='shipped').count())+"deliveries")
    admin_script.steps.add(ScriptStep.objects.create(
        script=admin_script,
        email=reminder_email,
        order=1,
        rule=ScriptStep.STRICT,
        start_offset=0,
        retry_offset=3600*24,
        ))
    user = User.objects.get(username="admin")

    transporter_script = Script.objects.create(
           slug="transporter",
           name="transporter script"
           )
    transporter_script.sites.add(Site.objects.get_current())
    delivery_poll = Poll.create_yesno('consignment_delivered', 'Has the consignment been delivered?',"Thanks for your response", [], user)
    transporter_script.steps.add(ScriptStep.objects.create(
           script=transporter_script,
           poll=delivery_poll,
           order=0,
           rule=ScriptStep.STRICT,
           start_offset=3600 * 24 * 3,
           retry_offset=3600 * 24,
           ))


        ###  consignee script ####

    consignee_script = Script.objects.create(
           slug="consignee",
           name="script for consignee",
           )
    consignee_script.sites.add(Site.objects.get_current())
    consignee_script.steps.add(ScriptStep.objects.create(
           script=consignee_script,
           message='consignment sent !',
           order=0,
           rule=ScriptStep.WAIT_MOVEON,
           start_offset=0,
           giveup_offset=3600 * 24 * 3,
           ))

    consignee_script.steps.add(ScriptStep.objects.create(
           script=consignee_script,
           poll=delivery_poll,
           order=1,
           rule=ScriptStep.STRICT,
           start_offset=0,
           retry_offset=3600 * 24,
           ))


def script_creation_handler(sender, **kwargs):
    #create script progress for admins , transporters  and consignees
    instance = kwargs['instance']
    supply_admins=Contact.objects.filter(group=Team.objects.get(name="supply_admins"))
    for admin in supply_admins:
        ScriptProgress.objects.create(script=Script.objects.get(slug="hq_supply_staff"),
                                              connection=instance.connection)
    ScriptProgress.objects.create(script=Script.objects.get(slug="transporter"),
                                          connection=instance.transporter.default_connection)
    ScriptProgress.objects.create(script=Script.objects.get(slug="consignee"),
                                          connection=instance.consignee.default_connection)




