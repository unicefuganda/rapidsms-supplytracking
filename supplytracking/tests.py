from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.core.exceptions import ValidationError

from script.utils.incoming import incoming_progress
from script.utils.outgoing import check_progress
from script.models import *
from script.signals import *

class ModelTest(TestCase):

    def setUp(self):
        test_backend=Backend.objects.create(name='TEST')
        user = User.objects.create_user('admin', 'test@test.com', '3b0la')
        transporter_connection = Connection.objects.create(identity='110000', backend=test_backend)
        consignee_connection = Connection.objects.create(identity='220000', backend=test_backend)
        admin1 = Connection.objects.create(identity='330000', backend=test_backend)
        admin2 = Connection.objects.create(identity='440000', backend=test_backend)
        date_shipped=datetime.datetime.now()
        connection = Connection.objects.create(identity='8675309', backend=Backend.objects.create(name='TEST'))
        ### transporter script###

        tranporter_script = Script.objects.create(
                slug="transporter",
                name="test script for transporter ",
        )
        delivery_poll=Poll.create_yesno('consignment_delivered', 'Has the consignment been delivered?', [], user)
        transporter_script.steps.add(ScriptStep.objects.create(
            script=transporter_script,
            poll=delivery_poll,
            order=0,
            rule=ScriptStep.STRICT,
            start_offset=3600*24*3,
            rentry_offset=3600*24,
            ))


        ###  consignee script ####

        consignee_script = Script.objects.create(
                slug="consignee",
                name="test  script for consignee",
        )

        consignee_script.steps.add(ScriptStep.objects.create(
            script=admin_consignee_script,
            message='consignment sent !',
            order=0,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=0,
            giveup_offset=3600*24*3,
            ))

        consignee_script.steps.add(ScriptStep.objects.create(
            script=consignee_script,
            poll=delivery_poll,
            order=1,
            rule=ScriptStep.STRICT,
            start_offset=0,
            rentry_offset=3600*24,
            ))


        ####  admins  script #####

        admin_script = Script.objects.create(
                slug="hq_supply_staff",
                name="test  script for head quarters supply staff",
        )

        email_1='You are reminded to upload the deliveries excel script'

        admin_script.steps.add(ScriptStep.objects.create(
            script=admin_script,
            email='You are reminded to upload the deliveries excel script',
            order=0,
            rule=ScriptStep.STRICT,
            start_offset=0,
            rentry_offset=3600*24, 
            ))
        email_2="you have "+str(Delivery.objects.filter(status='shipped').count())+"deliveries"
        admin_script.steps.add(ScriptStep.objects.create(
            script=admin_script,
            email=email_2,
            order=1,
            rule=ScriptStep.STRICT,
            start_offset=0,
            rentry_offset=3600*24,
            ))
        
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
        admin_script = Scripts.objects.get(slug='hq_supply_staff')
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

        # a script upload moves the admin script to the next step

        admin_1_response = check_progress(admins[0].default_connection)
        self.assertEquals(admin_2_response, admin_script.steps.get(order=1).email)

        #both admins should be on the same step
        self.assertEquals(
                ScriptProgress.objects.filter(script=admin_script, connection=admins[0].default_connection).step,
                ScriptProgress.objects.filter(script=admin_script, connection=admins[1].default_connection).step)

        self.assertEquals(admin_1_response, None)

        self.assertEquals(admin_2_response, None)
        self.elapseTime(86400)

        admin_1_response = check_progress(admins[0].default_connection)

        admin_2_response = check_progress(admins[1].default_connection)

        self.assertEquals(admin_1_response, admin_script.steps.get(order=1).email)

        self.assertEquals(admin_2_response, admin_script.steps.get(order=1).email)
        



    def testTransporterScript(self):
        delivery=Delivery.objects.get(waybill="test001")
        transporter_script=Scripts.objects.get(slug='consignee')
        progress = ScriptProgress.objects.create(connection=transporter_connection, script=transporter_script)
        response = check_progress(transporter_connection)
        self.assertEquals(response, None)
        #test start_offset offset
        self.elapseTime(259200)
        response = check_progress(transporter_connection)
        self.assertEquals(response, transporter_script.steps.get(order=0).poll.message)



    def testConsigneeScript(self):
        delivery=Delivery.objects.get(waybill="test001")
        consignee_script=Scripts.objects.get(slug='consignee')
        progress = ScriptProgress.objects.create(connection=transporter_connection, script=consignee_script)
        response = check_progress(transporter_connection)
        self.assertEquals(response, transporter_script.steps.get(order=0).poll.message)

    def testFulldeliveryScript(self):
        pass




        
