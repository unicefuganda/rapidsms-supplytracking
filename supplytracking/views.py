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

def parse_header_row(worksheet):
    fields=['transporter','waybill','consignee','date_shipped','status']
    field_cols={}
    for col in range(worksheet.ncols):
        value = sheet.cell(0, col).value
        for field in fields:
            if value.find(field) >= 0:
                field_cols[field]=col
    return field_cols


def parse_waybill(row):
    return worksheet.cell(row, cols['waybill']).value

def parse_transporter(row):
    return Contact.objects.get(name__icontains=worksheet.cell(row, cols['transporter']).value)

def parse_status(row):
    return worksheet.cell(row, cols['status']).value

def parse_consignee(row):
    return Contact.objects.get(name__icontains=(worksheet.cell(row, cols['consignee']).value))

def parse_date_shipped(row):
    return dateutil.parser.parse(worksheet.cell(row, cols['date_shipped']).value)

def handle_excel_file(file):
    if  file:
        excel = file.read()
        workbook = open_workbook(file_contents=excel)
        worksheet = workbook.sheet_by_index(0)


        cols=parse_header(worksheet)
        for row in range(sheet.nrows):
            delivery=Delivery.objects.create(waybill=parse_waybill(row),
                                               date_shipped=parse_date_shipped(row) ,
                                               consignee=parse_consignee(row),
                                               transporter=parse_transporter(row))


        if delivery:
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