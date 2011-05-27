from django.core.management.base import BaseCommand
from script.models import *
from poll.models import *

class Command(BaseCommand):

    def handle(self, **options):
        

        ####  admins  script #####

        admin_script = Script.objects.create(
                slug="hq_supply_staff",
                name="script for head quarters supply staff",
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