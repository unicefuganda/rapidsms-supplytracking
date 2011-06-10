from script.models import *
from supplytracking.models import Delivery
from django.contrib.auth.models import User
from django.conf import settings
from xlrd import open_workbook
from django.contrib.auth.models import Group
from rapidsms.models import Contact,Connection
from uganda_common.utils import assign_backend
from poll.models import Poll, ResponseCategory, Response, Category


def create_scripts():
    

    site = Site.objects.get_or_create(pk=settings.SITE_ID, defaults={
            'domain':'example.com',
        })
    admin_script = Script.objects.create(slug="hq_supply_staff",name="supply staff script")
    admin_script.sites.add(Site.objects.get_current())
    outstanding_delivery_email= Email.objects.create(subject='{% load msg_content %}SupplyTracking: {{ connection|email_subject }}',
                                         message='{{ connection|excel_reminder_msg }} {{ connection|outstanding_deliveries_msg }}')
    
    admin_script.steps.add(ScriptStep.objects.create(
        script=admin_script,
        email=outstanding_delivery_email,
        order=0,
        rule=ScriptStep.RESEND_GIVEUP,
        start_offset=0,
        retry_offset=3600*24,
        num_tries=100, 
        ))
    
    ### transporter script ####
    
    user = User.objects.get(username="admin")
    description = 'Transporters Poll'
    question = '{% load msg_content %}{{ connection|transporter_poll_msg }}'
    default_response = 'Thank you for your response'
    transporter_poll = Poll.objects.create(name=description,question=question,default_response=default_response,user=user)
    transporter_poll.add_yesno_categories()

    transporter_poll.sites.add(Site.objects.get_current())
    yes_category = transporter_poll.categories.get(name='yes')
    yes_category.name = 'delivered'
    yes_category.response = "Thank you for your response" 
    yes_category.priority = 4
    yes_category.color = '99ff77'
    yes_category.save()
    no_category = transporter_poll.categories.get(name='no')
    no_category.response = "Thank you for your response"
    no_category.name = 'undelivered'
    no_category.priority = 1
    no_category.color = 'ff9977'
    no_category.save()
    unknown_category = transporter_poll.categories.get(name='unknown')
    unknown_category.default = False
    unknown_category.priority = 2
    unknown_category.color = 'ffff77'
    unknown_category.save()
    unclear_category = Category.objects.create(
        poll=transporter_poll,
        name='unclear',
        default=True,
        color='ffff77',
        response='We have received but did not understand your response,please resend (with yes or no)',
        priority=3
    )
    
    transporter_script = Script.objects.create(slug="transporter",name="transporter script")
    transporter_script.sites.add(Site.objects.get_current())
#    
#    delivery_poll = Poll.create_yesno('consignment_delivered', 'Has the consignment been delivered?',"Thanks for your response", [], user)
    transporter_script.steps.add(ScriptStep.objects.create(
           script=transporter_script,
           poll=transporter_poll,
           order=0,
           rule=ScriptStep.RESEND_MOVEON,
           start_offset=3600 * 24 * 3,
           retry_offset=3600 * 24,
           num_tries=3,
           ))


        ###  consignee script ####
        
    description = 'Consignees Poll'
    question = '{% load msg_content %}{{ connection|consignee_poll_msg }}'
    consignee_poll = Poll.objects.create(name=description,question=question,default_response=default_response,user=user)
    consignee_poll.add_yesno_categories()

    consignee_poll.sites.add(Site.objects.get_current())
    yes_category = consignee_poll.categories.get(name='yes')
    yes_category.name = 'delivered'
    yes_category.response = "Thank you for your response" 
    yes_category.priority = 4
    yes_category.color = '99ff77'
    yes_category.save()
    no_category = consignee_poll.categories.get(name='no')
    no_category.response = "Thank you for your response"
    no_category.name = 'undelivered'
    no_category.priority = 1
    no_category.color = 'ff9977'
    no_category.save()
    unknown_category = consignee_poll.categories.get(name='unknown')
    unknown_category.default = False
    unknown_category.priority = 2
    unknown_category.color = 'ffff77'
    unknown_category.save()
    unclear_category = Category.objects.create(
        poll = consignee_poll,
        name = 'unclear',
        default = True,
        color = 'ffff77',
        response = 'We have received but did not understand your response,please resend (with no or <waybill> COMPLETE <waybill> DAMAGED)',
        priority = 3
    )
    
    consignee_script = Script.objects.create(slug="consignee",name="script for consignee",)
    consignee_script.sites.add(Site.objects.get_current())
    
    consignee_script.steps.add(ScriptStep.objects.create(
           script=consignee_script,
           poll=consignee_poll,
           order=0,
           rule=ScriptStep.STRICT,
           start_offset=3600 * 24 * 3,
           retry_offset=3600 * 24,
           ))

    #create script progress for admins
    supply_admins=Contact.objects.filter(groups=Group.objects.filter(name="supply_admins"))
    for admin in supply_admins:
        scriptprogress,progress_created=ScriptProgress.objects.get_or_create(script=Script.objects.get(slug="hq_supply_staff"),
                                                  connection=admin.default_connection)



def load_excel_file(file, group_name):
    if  file:
            excel = file.read()
            workbook = open_workbook(file_contents=excel)
            sheet = workbook.sheet_by_index(0)
            #iterate over the first row
            #and get the cell containing waybills
            name_col = ''
            telephone_col = ''

            for col in range(sheet.ncols):
                value = sheet.cell(0, col).value
                if value.find("Company Name") >= 0:
                    name_col = col
                if value.find("Telephone") >= 0:
                    telephone_col = col

            group, group_created = Group.objects.get_or_create(name=group_name)
#            consignee,consignee_created=Group.objects.get_or_create(name='consignee')
            for row in range(sheet.nrows)[1:]:
                telephone=str(sheet.cell(row, telephone_col).value)
                if len(telephone)>0:
                    contact,contact_created=Contact.objects.get_or_create(name=str(sheet.cell(row, name_col).value).lower())
                    #print 'adding '+ contact.name
                    if contact_created:
                        contact.groups.add(group)
                    backend=assign_backend(telephone)[1]
                    connection,connection_created=Connection.objects.get_or_create(identity=str(sheet.cell(row, telephone_col)),backend=backend)
                    if connection_created:
                        connection.contact=contact
                        connection.save()



