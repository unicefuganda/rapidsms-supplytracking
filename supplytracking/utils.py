from script.models import *
from status160.models import Team
from supplytracking.models import *
from django.contrib.auth.models import User
def create_scripts():
    
    admin_script = Script.objects.create(
                slug="hq_supply_staff",
                name="script for head quarters supply staff",
        )
    

    admin_script.steps.add(ScriptStep.objects.create(
        script=admin_script,
        email='You are reminded to upload the deliveries excel script',
        order=0,
        rule=ScriptStep.STRICT,
        start_offset=0,
        retry_offset=3600*24,
        ))
    email_2="you have "+str(Delivery.objects.filter(status='shipped').count())+"deliveries"
    admin_script.steps.add(ScriptStep.objects.create(
        script=admin_script,
        email=email_2,
        order=1,
        rule=ScriptStep.STRICT,
        start_offset=0,
        retry_offset=3600*24,
        ))
    user = User.objects.get(username="admin")

    transporter_script = Script.objects.create(
           slug="transporter",
           name="transporter script",
           )

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







