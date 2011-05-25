import rapidsms
import datetime

from rapidsms.apps.base import AppBase
from .models import *

class App (AppBase):

    def handle (self, message):
        
            admin_progress=ScriptProgress.objects.get_or_create(script=Script.objects.get(slug="hq_supply_staff"),
                                          connection=message.connection)
            return True

