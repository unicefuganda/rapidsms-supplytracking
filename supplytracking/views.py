from django.shortcuts import render_to_response
from django.template import RequestContext
from django import forms
from django.db.models.signals import post_save

from xlrd import open_workbook
from uganda_common.utils import assign_backend
import dateutil
from supplytracking.utils import script_creation_handler

class UploadForm(forms.Form):
    nodelivery = forms.BooleanField(widget=forms.CheckboxInput(),
                                    label='No delivery', required=False)
    excel_file = forms.FileField(label="Excel File")


def handle_excel_file(file):
    if  file:
        excel = file.read()
        workbook = open_workbook(file_contents=excel)
        sheet = workbook.sheet_by_index(0)
        #iterate over the first row
        #and get the cell containing waybills
        way_bill_col = ''
        consignee_col = ''
        date_shipped_col = ''

        for col in range(sheet.ncols):
            value = sheet.cell(0, col).value
            if value.find("waybill") >= 0:
                way_bill_col = col
            if value.find("consignee") >= 0:
                consignee_col = col
            if value.find("transporter") >= 0:
                transporter_col = col
            if value.find("shipped") >= 0 and value.find("date"):
                date_shipped_col = col

            #create delivery objects

        for row in range(sheet.nrows):
            transporter_connection = Connection.objects.create(identity=sheet.cell(row, transporter_col),
                                                               backend=assign_backend(sheet.cell(row, transporter_col)),
                                                               contact=Contact.objects.create(name='anon_transporter',group=Team.objects.get_or_create(name='consignee')))
            consignee_connection = Connection.objects.create(identity=sheet.cell(row, consignee_col),
                                                             backend=sheet.cell(row, consignee_col),
                                                             contact=Contact.objects.create(name='anon_consignee',group=Team.objects.get_or_create(name='consignee')))
            delivery = Delivery.objects.create(waybill=sheet.cell(row, way_bill_col),
                                               date_shipped=dateutil.parser.parse(
                                                       sheet.cell(row, date_shipped_col).value),
                                               consignee=consignee_connection.contact,
                                               transporter=transporter_connection.contact)
            post_save.connect(script_creation_handler,sender=delivery)



def index(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            parse_excel_file(request.FILES['excel_file'])
        else:
            form = UploadForm()

    form = UploadForm()
    return render_to_response('supplytracking/index.html', {'form':form}, context_instance=RequestContext(request))