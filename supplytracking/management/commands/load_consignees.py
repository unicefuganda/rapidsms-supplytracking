
import traceback
from optparse import OptionParser, make_option
from django.core.management.base import BaseCommand




class Command(BaseCommand):

    help = """loads all the consignees into the database
    """


    option_list = BaseCommand.option_list + (
    make_option("-f", "--file", dest="path"),
    )

    def handle(self, **options):
        path=options["path"]
        try:
            excel_file = open(path)
            load_consignees(excel_file)
            print "consignees successfully added!"
        except Exception, exc:
            print traceback.format_exc(exc)