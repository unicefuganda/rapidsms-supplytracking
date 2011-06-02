from django.shortcuts import render_to_response
from django.template import RequestContext
from django import forms
from django.db.models.signals import post_save
from django.forms.util import ErrorList

from xlrd import open_workbook
from uganda_common.utils import assign_backend
import dateutil
from supplytracking.utils import script_creation_handler
from supplytracking.models import *
import datetime
from script.models import *

class UploadForm(forms.Form):
    nodelivery = forms.BooleanField(widget=forms.CheckboxInput(),
                                    label='No delivery', required=False)
    excel_file = forms.FileField(label="Excel File",required=False)
    def clean(self):
        excel = self.cleaned_data['excel_file']
        if excel.name.rsplit('.')[1] != 'xls':
                msg=u'Upload valid excel file !!!'
                self._errors["excel_file"]=ErrorList([msg])
                return ''
        return self.cleaned_data


def parse_header_row(worksheet):
    fields=['transporter','waybill','consignee','date_shipped','status']
    field_cols={}
    for col in range(worksheet.ncols):
        value = worksheet.cell(0, col).value

        for field in fields:
            if value.lower().find(field) >= 0:
                field_cols[field]=col
    return field_cols


def parse_waybill(row,worksheet,cols):
    return worksheet.cell(row, cols['waybill']).value

def parse_transporter(row,worksheet,cols):
    try:
        return Contact.objects.get(name__icontains=worksheet.cell(row, cols['transporter']).value)
    except:
        return None

def parse_status(row,worksheet,cols):
    return worksheet.cell(row, cols['status']).value

def parse_consignee(row,worksheet,cols):
    return Contact.objects.get(name__icontains=(worksheet.cell(row, cols['consignee']).value))

def parse_date_shipped(row,worksheet,cols):
    try:
        date=dateutil.parser.parse(worksheet.cell(row, cols['date_shipped']).value)
    except:
        date=datetime.datetime.now()
    return date

def handle_excel_file(file):
    if file:
        excel = file.read()
        workbook = open_workbook(file_contents=excel)
        worksheet = workbook.sheet_by_index(0)
        cols=parse_header_row(worksheet)
        deliveries=[]
        for row in range(worksheet.nrows)[1:]:
            delivery=Delivery.objects.create(waybill=parse_waybill(row,worksheet,cols),
                                               date_shipped=parse_date_shipped(row,worksheet,cols) ,
                                               consignee=parse_consignee(row,worksheet,cols),)
                                               #transporter=parse_transporter(row,worksheet,cols))


            post_save.connect(script_creation_handler,sender=delivery)
            deliveries.append(delivery.waybill)
        return 'deliveries with waybills ' +' ,'.join(deliveries) + " have been uploaded !"
    else:
        return "Invalid file"



def index(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get('nodelivery', False):
                ##increase the script session for admin retry by 1 day
                admins=ScriptSession.objects.all()
            else:

                message= handle_excel_file(request.FILES['excel_file'])
                return render_to_response('supplytracking/index.html', {'form':form,'message':message}, context_instance=RequestContext(request))

        else:
            form = UploadForm()


    form = UploadForm()
    return render_to_response('supplytracking/index.html', {'form':form}, context_instance=RequestContext(request))