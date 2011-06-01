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
    reminder_email=Email.objects.create(subject="SupplyTracking: Excel Upload reminder" ,message="You are reminded to upload the deliveries excel script")
    admin_script.steps.add(ScriptStep.objects.create(
        script=admin_script,
        email=reminder_email,
        order=0,
        rule=ScriptStep.STRICT,
        start_offset=0,
        retry_offset=3600*24,
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

def load_consignees(file):
    if  file:
            excel = file.read()
            workbook = open_workbook(file_contents=excel)
            sheet = workbook.sheet_by_index(0)
            #iterate over the first row
            #and get the cell containing waybills
            name_col = ''
            telephone_col = ''
            date_shipped_col = ''

            for col in range(sheet.ncols):
                value = sheet.cell(0, col).value
                if value.find("Company Name") >= 0:
                    name_col = col
                if value.find("Telephone") >= 0:
                    telephone_col = col
            consignee=Group.objects.get_or_create(name='consignee')
            for row in range(sheet.nrows):
                contact=Contact.objects.create(name=sheet.cell(row, name_col).value,group=consignee)
                connection=Connection.objects.create(identity=sheet.cell(row, transporter_col),
                                                                   backend=assign_backend(sheet.cell(row, telephone_col).value))
                connection.contact=contact
                connection.save()




