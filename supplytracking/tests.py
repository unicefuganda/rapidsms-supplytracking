from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import post_save

from script.utils.incoming import incoming_progress
from script.utils.outgoing import check_progress
from script.models import *
from supplytracking.models import *
from supplytracking.utils import create_scripts,load_consignees,script_creation_handler
from supplytracking.views import UploadForm
from django.contrib.auth.models import Group
from django.db import connection
from rapidsms.models import Connection,Contact
from supplytracking.views import UploadForm, handle_excel_file
from django.db import connection
import os
from supplytracking.views import handle_excel_file



class ModelTest(TestCase):

     #fixtures = ['fixtures/test_supplytracking.json']
     def setUp(self):
         create_scripts()
         consignee_file=open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'consignees.xls'),'rb')
         load_consignees(consignee_file)



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
        admins = Contact.objects.filter(groups=Group.objects.filter(name='supply_admin'))
        progress = []
        for admin in admins:
            progress.append(ScriptProgress.objects.create(connection=admin.default_connection, script=admin_script))
        response = check_progress(admins[0].default_connection)
        progress[0] = ScriptProgress.objects.get(connection=admins[0].default_connection, script=admin_script)
        self.assertEquals(progress[0].step.order, 0)
        self.assertEquals(response, admin_script.steps.get(order=0).email)
        
        #wait for one day, the script should re-send the reminder to the admins
        self.elapseTime(progress[0], 86401)
        response = check_progress(admins[0].default_connection)
        self.assertEquals(response, admin_script.steps.get(order=0).email)
        
        # no excel upload does not move the script to next step for all admins
        response = check_progress(admins[1].default_connection)
        progress[1] = ScriptProgress.objects.get(connection=admins[1].default_connection, script=admin_script)
        self.assertEquals(progress[1].step.order, 0)
        
        #upload a sheet and the admins should be moved to next step after a three day time offset
        upload_file = open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'excel.xls'), 'rb')
        file_dict = {'excel_file': SimpleUploadedFile(upload_file.name, upload_file.read())}
        form = UploadForm({},file_dict)
        self.assertTrue(form.is_valid())
        msg = handle_excel_file(form.cleaned_data['excel_file'])
        
        # a sheet upload waits for time_offset before moving admins to the next step
        response = check_progress(admins[1].default_connection)
        progress[1] = ScriptProgress.objects.get(connection=admins[1].default_connection, script=admin_script)
        self.assertEquals(progress[1].step.order, 0)
        
        # after 3 days, admins should be moved to the next step
        self.elapseTime(progress[1], 259201)
        response = check_progress(admins[1].default_connection)
        progress[1] = ScriptProgress.objects.get(connection=admins[1].default_connection, script=admin_script)
        self.assertEquals(progress[1].step.order, 1)
        self.assertEquals(response, admin_script.steps.get(order=1).email)


        #all admins should be on the same step and all should receive an email of outstanding deliveries
        self.assertEquals(
                ScriptProgress.objects.filter(script=admin_script, connection=admins[0].default_connection).step,
                ScriptProgress.objects.filter(script=admin_script, connection=admins[1].default_connection).step)
        self.assertEquals(check_progress(admins[0].default_connection), check_progress(admins[0].default_connection))
        self.assertEquals(check_progress(admins[0].default_connection), admin_script.steps.get(order=1).email)

     def testTransporterScript(self):
        delivery=Delivery.objects.get(waybill="del001")
        transporter_script=Script.objects.get(slug='transporter')
        transporter_connection = Contact.objects.get(name=delivery.transporter).default_connection
        progress = ScriptProgress.objects.create(connection=transporter_connection, script=transporter_script)
        response = check_progress(transporter_connection)
        self.assertEquals(progress.step, None)
        self.assertEquals(response, None)
        #wait 3 days
        self.elapseTime(progress, 259201)
        response = check_progress(transporter_connection)
        progress = ScriptProgress.objects.create(connection=transporter_connection, script=transporter_script)
        self.assertEquals(progress.step.order, 0)
        self.assertEquals(response, 'Has the consignment been delivered?')



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
     def testExcelImport(self):
        upload_file = open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'excel.xls'), 'rb')
        file_dict = {'excel_file': SimpleUploadedFile(upload_file.name, upload_file.read())}
        form = UploadForm({},file_dict)
        self.assertTrue(form.is_valid())
        #test Delivery object creation
        
        msg=handle_excel_file(form.cleaned_data['excel_file'])

        self.assertEquals(msg, "deliveries with waybills KP/WB11/00034 ,KP/WB11/00035 ,KP/WB11/00036 have been uploaded !")

        deliveries =Delivery.objects.all()

        #make sure 3 deliveries were created
        self.assertEqual(deliveries.count(),3)

        #make sure all the deliveries have consignees
        for delivery in deliveries:
            pass
        

     










