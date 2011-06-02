from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile


from script.utils.incoming import incoming_progress
from script.utils.outgoing import check_progress
from script.models import *
from supplytracking.models import *
from supplytracking.utils import create_scripts
from supplutracking.views import UploadForm


class ModelTest(TestCase):

     #fixtures = ['test_supplytracking.json']
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
        #prompt for excel upload
        admins = Contact.objects.filter(group=Group.objects.get(slug='admin_supply'))

        admin_1_response = check_progress(admins[0].default_connection)

        admin_2_response = check_progress(admins[1].default_connection)

        #have the admins been prompted to upload excel sheet?

        self.assertEquals(admin_1_response, admin_script.steps.get(order=0).email)

        self.assertEquals(admin_2_response, admin_script.steps.get(order=0).email)

        #a sheet is uploaded  when a new delivery script is created

        delivery = Delivery.objects.create(waybill="del001", date_shipped=date_shipped, consignee=Contact.objects.filter(group=Group.objects.get(name='consignee'))[0],
                                           transporter=Contact.objects.filter(group=Group.objects.get(name='transporter'))[0])

        # a script upload moves the admin script to the next step

        admin_1_response = check_progress(admins[0].default_connection)
        self.assertEquals(admin_2_response, admin_script.steps.get(order=1).email)

        #both admins should be on the same step
        self.assertEquals(
                ScriptProgress.objects.filter(script=admin_script, connection=admins[0].default_connection).step,
                ScriptProgress.objects.filter(script=admin_script, connection=admins[1].default_connection).step)


        admin_1_response = check_progress(admins[0].default_connection)

        self.assertEquals(admin_1_response, admin_script.steps.get(order=1).email)

        self.assertEquals(admin_2_response, admin_script.steps.get(order=1).email)




     def testTransporterScript(self):
        delivery=Delivery.objects.get(waybill="del001")
        transporter_script=Script.objects.get(slug='consignee')
        progress = ScriptProgress.objects.create(connection=transporter_connection, script=transporter_script)
        response = check_progress(transporter_connection)
        self.assertEquals(response, None)
        #test start_offset offset
        self.elapseTime(259200)
        response = check_progress(transporter_connection)
        self.assertEquals(response, transporter_script.steps.get(order=0).poll.message)



     def testConsigneeScript(self):
        delivery=Delivery.objects.get(waybill="del001")
        consignee_script=Script.objects.get(slug='consignee')
        progress = ScriptProgress.objects.create(connection=transporter_connection, script=consignee_script)
        response = check_progress(transporter_connection)
        self.assertEquals(response, transporter_script.steps.get(order=0).poll.message)

     def testFulldeliveryScript(self):
        admin_script = Script.objects.get(slug='hq_supply_staff')
        #prompt for excel upload
        admins = Contact.objects.filter(group=Group.objects.get(slug='unicef_supply'))
        for admin in admins:
            progress = ScriptProgress.objects.create(connection=admin.default_connection, script=admin_script)

        admin_1_response = check_progress(admins[0].default_connection)

        admin_2_response = check_progress(admins[1].default_connection)

        #have the admins been prompted to upload excel sheet?

        self.assertEquals(admin_1_response, admin_script.steps.get(order=0).email)

        self.assertEquals(admin_2_response, admin_script.steps.get(order=0).email)

        #a sheet is uploaded  when a new delivery script is created

        delivery = Delivery.objects.create(waybill="test001", date_shipped=date_shipped, consignee=consignee_connection,
                                           transporter=transporter_connection)

        # a script upload should start the the consignee script
     def test_form(self):
        upload_file = open('fixtures/excel.xls', 'rb')
        file_dict = {'excel_file': SimpleUploadedFile(upload_file.name, upload_file.read())}
        form = MyForm(file_dict)
        self.assertTrue(form.is_valid())
        #test Delivery object creation
        
        msg=handle_excel_file(form.cleaned_data['excel_file'])

        self.assertEquals(msg, "deliveries with waybills KP/WB11/00034 ,KP/WB11/00035 ,KP/WB11/00036 have been uploaded !")
        
        

     










