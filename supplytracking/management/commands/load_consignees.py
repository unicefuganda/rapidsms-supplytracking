from xlrd import open_workbook
from django.contrib.auth.models import Group
import traceback
from optparse import OptionParser, make_option
from django.core.management.base import BaseCommand
from rapidsms.models import Contact,Connection
from uganda_common.utils import assign_backend
def load_consignees(file):
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

            consignee=Group.objects.get_or_create(name='consignee')[0]
            for row in range(sheet.nrows)[1:]:
                print str(sheet.cell(row, name_col).value)
                contact=Contact.objects.get_or_create(name=str(sheet.cell(row, name_col).value))[0]
                print 'adding '+ contact.name
                contact.groups.add(consignee)
                connection=Connection.objects.create(identity=str(sheet.cell(row, telephone_col)),
                                                                   backend=assign_backend(str(sheet.cell(row, telephone_col).value))[1])
                connection.contact=contact
                connection.save()


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