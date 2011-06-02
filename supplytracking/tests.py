from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.core.exceptions import ValidationError

from script.utils.incoming import incoming_progress
from script.utils.outgoing import check_progress
from script.models import *
from supplytracking.models import *
from supplytracking.utils import create_scripts
from django.contrib.auth.models import Group
from django.db import connection


class ModelTest(TestCase):

#     fixtures = ['test_supplytracking.json']
     def setUp(self):
         create_scripts()


     def fakeIncoming(self, message, connection=None):
        if connection is None:
            connection = Connection.objects.all()[0]
        # if so, process it
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=connection, text=message)
        return incomingmessage

     def elapseTime(self, progress, seconds):
        """
        This hack mimics the progression of time, from the perspective of a linear test case,
        by actually *subtracting* from the value that's currently stored (usually datetime.datetime.now())
        """
        cursor = connection.cursor()
        newtime = progress.time - datetime.timedelta(seconds=seconds)
        cursor.execute("update script_scriptprogress set time = '%s' where id = %d" %
                       (newtime.strftime('%Y-%m-%d %H:%M:%S.%f'), progress.pk))
        try:
            session = ScriptSession.objects.get(connection=progress.connection, end_time=None)
            session.start_time = session.start_time - datetime.timedelta(seconds=seconds)
            session.save()
        except ScriptSession.DoesNotExist:
            pass

     def testAdminScript(self):

        admin_script = Script.objects.get(slug='hq_supply_staff')
        admins = Contact.objects.filter(groups=Group.objects.get(name='supply_admin'))
        for admin in admins:
            ScriptProgress.objects.create(connection=admin.default_connection, script=admin_script)
        response = check_progress(admins[0].default_connection)
        #have the admins been prompted to upload excel sheet?
        self.assertEquals(response, admin_script.steps.get(order=0).email)
#        wait a day without response
        progress = ScriptProgress.objects.get(connection=admins[0].default_connection, script=admin_script)
        self.elapseTime(progress, 86401)
        response = check_progress(admins[0].default_connection)
        self.assertEquals(response, admin_script.steps.get(order=0).email)
        
        # no excel upload does not move the script to next step for all admins
        admin1_response = check_progress(admins[1].default_connection)
        progress = ScriptProgress.objects.get(connection=admins[1].default_connection)
        self.assertEquals(progress.step.order, 0)

        #a sheet is uploaded  when a new delivery script is created
        date_shipped = '2011-06-01'
        delivery = Delivery.objects.create(waybill="del000", date_shipped=date_shipped, consignee=Contact.objects.filter(groups=Group.objects.get(name='consignee'))[0],
                                           transporter=Contact.objects.filter(groups=Group.objects.get(name='transporter'))[0])

        # a script upload moves the admin script to the next step
        admin1_response = check_progress(admins[1].default_connection)
#        self.assertEquals(admin1_response, admin_script.steps.get(order=1).email)
        progress = ScriptProgress.objects.get(connection=admins[1].default_connection)
        self.assertEquals(progress.step.order, 1)

        #both admins should be on the same step
        self.assertEquals(
                ScriptProgress.objects.filter(script=admin_script, connection=admins[0].default_connection).step,
                ScriptProgress.objects.filter(script=admin_script, connection=admins[1].default_connection).step)


        admin_1_response = check_progress(admins[0].default_connection)
        self.assertEquals(admin_1_response, admin_script.steps.get(order=1).email)
        self.assertEquals(admin_2_response, admin_script.steps.get(order=1).email)




     def testTransporterScript(self):
        delivery=Delivery.objects.get(waybill="del001")
        transporter_script=Script.objects.get(slug='transporter')
        transporter_connection = Contact.objects.get(name=delivery.transporter).default_connection
        progress = ScriptProgress.objects.create(connection=transporter_connection, script=transporter_script)
        response = check_progress(transporter_connection)
        self.assertEquals(response, None)
        self.elapseTime(progress, 259200)
        response = check_progress(transporter_connection)
        self.assertEquals(response, transporter_script.steps.get(order=0).poll)



     def testConsigneeScript(self):
        delivery=Delivery.objects.get(waybill="del001")
        consignee_script=Script.objects.get(slug='consignee')
        consignee_connection = Contact.objects.get(name=delivery.consignee).default_connection
        progress = ScriptProgress.objects.create(connection=consignee_connection, script=consignee_script)
        response = check_progress(consignee_connection)
        self.assertEquals(response, consignee_script.steps.get(order=0).message)

#     def testFulldeliveryScript(self):
#        admin_script = Script.objects.get(slug='hq_supply_staff')
#        admins = Contact.objects.filter(groups=Group.objects.get(name='supply_admin'))
#        for admin in admins:
#            progress = ScriptProgress.objects.create(connection=admin.default_connection, script=admin_script)
#        consignee_connection = Contact.objects.get(name=delivery.consignee).default_connection        
#        transporter_connection = Contact.objects.get(name=delivery.transporter).default_connection
#        date_shipped = '2011-06-01'
#        delivery = Delivery.objects.create(waybill="test001", date_shipped=date_shipped, consignee=consignee_connection,
#                                           transporter=transporter_connection)

        # a script upload should start the the consignee script









