from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import post_save

from script.utils.incoming import incoming_progress
from script.utils.outgoing import check_progress
from script.models import *
from supplytracking.models import *
from supplytracking.utils import create_scripts,load_excel_file
from supplytracking.views import UploadForm
from django.contrib.auth.models import Group
from django.db import connection
from rapidsms.models import Connection,Contact
from supplytracking.views import UploadForm, handle_excel_file
from django.db import connection
import os
from supplytracking.views import handle_excel_file
from django.template import Template, Context



class ModelTest(TestCase):

     #fixtures = ['fixtures/test_supplytracking.json']
     def setUp(self):
         create_scripts()
         consignee_file=open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'consignees.xls'),'rb')
         load_excel_file(consignee_file, 'consignee')
         transporter_file=open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'transporters.xls'),'rb')
         load_excel_file(transporter_file, 'transporter')


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
        subject = Template(response.subject)
        self.assertEquals(subject.render(Context(admins[0].default_connection)), 'SupplyTracking: Reminder to Upload Consignments Excel Sheet')
        
        #wait for one day, the script should re-send the reminder to the admins to upload excel
        self.elapseTime(progress[0], 86401)
        response = check_progress(admins[0].default_connection)
        self.assertEquals(progress[0].step.order, 0)
        subject = Template(response.subject)
        self.assertEquals(subject.render(Context(admins[0].default_connection)), 'SupplyTracking: Reminder to Upload Consignments Excel Sheet')
        
        #upload a sheet we expect delivery objects to be created but not necessary trigger off any scripts
        upload_file = open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'excel.xls'), 'rb')
        file_dict = {'excel_file': SimpleUploadedFile(upload_file.name, upload_file.read())}
        form = UploadForm({},file_dict)
        self.assertTrue(form.is_valid())
        msg = handle_excel_file(form.cleaned_data['excel_file'])
        
        response = check_progress(admins[0].default_connection)
        progress[0] = ScriptProgress.objects.get(connection=admins[0].default_connection, script=admin_script)
        self.assertEquals(progress[0].step.order, 0)
        
        #wait for one day, the script should re-send the reminder to the admins to upload excel
        self.elapseTime(progress[0], 86401)
        response = check_progress(admins[0].default_connection)
        self.assertEquals(progress[0].step.order, 0)
        subject = Template(response.subject)
        self.assertEquals(subject.render(Context(admins[0].default_connection)), 'SupplyTracking: Reminder to Upload Consignments Excel Sheet')
        
        #wait for one day, upload another excel
        self.elapseTime(progress[0], 86401)
        upload_file = open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'excel2.xls'), 'rb')
        file_dict = {'excel_file': SimpleUploadedFile(upload_file.name, upload_file.read())}
        form = UploadForm({},file_dict)
        self.assertTrue(form.is_valid())
        msg = handle_excel_file(form.cleaned_data['excel_file'])
                
#        # after 1 more day
#        self.elapseTime(progress[0], 86401)
#        response = check_progress(admins[0].default_connection)
#        self.assertEquals(progress[0].step.order, 0)
#        subject = Template(response.subject)
#        print Delivery.objects.all().values_list('date_uploaded')
#        self.assertEquals(subject.render(Context(admins[0].default_connection)), 'SupplyTracking: Outstanding Deliveries Report')
#        #new delivery objects are thrown into backlog since there is already an active script progression for admins
#        self.assertEquals(DeliveryBackLog.objects.get(delivery__waybill='kp/wb11/00037'), Delivery.objects.get(waybill='kp/wb11/00037'))

     def testTransporterScript(self):
         #upload excel, this should result into creation of a delivery
        upload_file = open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'excel.xls'), 'rb')
        file_dict = {'excel_file': SimpleUploadedFile(upload_file.name, upload_file.read())}
        form = UploadForm({},file_dict)
        self.assertTrue(form.is_valid())
        msg = handle_excel_file(form.cleaned_data['excel_file'])
        
        #wait one day and upload another excel
        progress = ScriptProgress.objects.get(connection=Contact.objects.get(name='3ways shipping').default_connection)
        self.elapseTime(progress, 86401)
        upload_file = open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'excel2.xls'), 'rb')
        file_dict = {'excel_file': SimpleUploadedFile(upload_file.name, upload_file.read())}
        form = UploadForm({},file_dict)
        self.assertTrue(form.is_valid())
        msg = handle_excel_file(form.cleaned_data['excel_file'])
        
        #transporter has different shipments in shipped status
        self.assertEquals(Delivery.objects.filter(transporter=Contact.objects.get(name='3ways shipping'),status='S').count(), 4)
        
        #transporter does not advance to step 0 before the start_offset time has expired
        transporter_script=Script.objects.get(slug='transporter')
        default_connection = Contact.objects.get(name='3ways shipping').default_connection
        transporter_connection = default_connection.pk
        response = check_progress(transporter_connection)
        self.assertEquals(progress.step, None)
        self.assertEquals(response, None)
        
        #elapse 3 days
        self.elapseTime(progress, 259201)
        
        #transporter should advance to step 0 of transporter script for deliveries uploaded 3 or more days ago
        response = check_progress(transporter_connection)
        progress = ScriptProgress.objects.get(connection=transporter_connection, script=transporter_script)
        self.assertEquals(progress.step.order, 0)
        response_msg = Template(response)
        self.assertEquals(response_msg.render(Context(transporter_connection)), 'Has the consignment been delivered?')
        self.assertEquals(Delivery.objects.filter(transporter=Contact.objects.get(name='3ways shipping'), status='S').count(), 4)
        self.assertEquals(DeliveryBackLog.objects.get(delivery__waybill='kp/wb11/00037'), Delivery.objects.get(waybill='kp/wb11/00037'))
        
        #transporter sending delivery message does not affect delivery status
        incomingmessage = self.fakeIncoming('kp/wb11/00034 Delivered')
        response_message = incoming_progress(incomingmessage)
        self.assertEquals(response_message, "Thanks for your response")
        progress = ScriptProgress.objects.get(connection=transporter_connection, script=transporter_script)
        self.assertEquals(Delivery.objects.get(waybill='kp/wb11/00034').status, 'S')
        #new delivery objects are thrown into backlog since there is already an active script progression for admins
        self.assertEquals(DeliveryBackLog.objects.get(delivery__waybill='kp/wb11/00037'), Delivery.objects.get(waybill='kb/wb11/00037'))

     def testConsigneeScript(self):
        #upload excel, this should result into creation of a delivery
        upload_file = open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'excel.xls'), 'rb')
        file_dict = {'excel_file': SimpleUploadedFile(upload_file.name, upload_file.read())}
        form = UploadForm({},file_dict)
        self.assertTrue(form.is_valid())
        msg = handle_excel_file(form.cleaned_data['excel_file'])
        
        #wait one day and upload another excel
        self.elapseTime(progress[0], 86401)
        upload_file = open(os.path.join(os.path.join(os.path.realpath(os.path.dirname(__file__)),'fixtures'),'excel2.xls'), 'rb')
        file_dict = {'excel_file': SimpleUploadedFile(upload_file.name, upload_file.read())}
        form = UploadForm({},file_dict)
        self.assertTrue(form.is_valid())
        msg = handle_excel_file(form.cleaned_data['excel_file'])
        
        #consignee has different shipments in shipped status
        self.assertEquals(Delivery.objects.filter(consignee=Contact.objects.get(name='action against hunger', status='S')).count(), 2)
        
        #consignee has not yet advanced into the script (step 0)
        consignee_script=Script.objects.get(slug='consignee')
        consignee_connection = Contact.objects.get(name='action against hunger').default_connection
        progress = ScriptProgress.objects.create(connection=consignee_connection, script=consignee_script)
        response = check_progress(consignee_connection)
        self.assertEquals(progress.step, None)
        self.assertEquals(response, None)
        
        #elapse 3 days
        self.elapseTime(progress, 259201)
        
        #consignee should advance to step 0 of consignee script for deliveries uploaded 3 more days ago
        response = check_progress(consignee_connection)
        progress = ScriptProgress.objects.get(connection=consignee_connection, script=consignee_script)
        self.assertEquals(progress.step.order, 0)
        self.assertEquals(response, 'Has the consignment been delivered?')
        self.assertEquals(Delivery.objects.filter(consignee=Contact.objects.get(name='action against hunger', status='S')).count(), 2)
        self.assertEquals(DeliveryBackLog.objects.get(delivery__waybill='kp/wb11/00037'), Delivery.objects.get(waybill='kp/wb11/00037'))
        
        #consignee sending in a delivery message should complete the script for transporter and consignee and mark orders as delivered
        incomingmessage = self.fakeIncoming('kp/wb11/00034 COMPLETE kb/wb11/00037 COMPLETE')
        response_message = incoming_progress(incomingmessage)
        self.assertEquals(response_message, "Thanks for your response")
        progress = ScriptProgress.objects.get(connection=consignee_connection, script=consignee_script)
        self.assertEquals(Delivery.objects.filter(consignee=Contact.objects.get(name='action against hunger', status='D')).count(), 2)
        self.assertEquals(DeliveryBackLog.objects.filter(delivery__consignee=Contact.objects.get(name='action against hunger')), None)
        
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
        

     










