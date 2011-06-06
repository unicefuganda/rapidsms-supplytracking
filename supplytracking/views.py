from django.shortcuts import render_to_response
from django.template import RequestContext
from django import forms
from django.forms.util import ErrorList
from django.db import IntegrityError

from xlrd import open_workbook
from uganda_common.utils import assign_backend
import dateutil
from supplytracking.utils import script_creation_handler,load_excel_file
from supplytracking.models import *
import datetime
from script.models import *

class UploadForm(forms.Form):
    nodelivery = forms.BooleanField(widget=forms.CheckboxInput(),
                                    label='No delivery', required=False)
    excel_file = forms.FileField(label="Excel File",required=False)
    def clean(self):
        excel = self.cleaned_data.get('excel_file',None)
        if excel and excel.name.rsplit('.')[1] != 'xls':
                msg=u'Upload valid excel file !!!'
                self._errors["excel_file"]=ErrorList([msg])
                return ''
        return self.cleaned_data

class ConsigneeForm(forms.Form):
    consignee_file = forms.FileField(label="Consignees Excel File",required=False)
    def clean(self):
        excel = self.cleaned_data.get('consignee_file',None)
        if excel and excel.name.rsplit('.')[1] != 'xls':
                msg=u'Upload valid excel file !!!'
                self._errors["consignee_file"]=ErrorList([msg])
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
        contact,contact_created=Contact.objects.get_or_create(name=str(worksheet.cell(row, cols['transporter']).value))
        if contact_created:
            transporter,transporter_created=Group.objects.get_or_create(name='transporter')
            contact.groups.add(transporter)
            backend=assign_backend(telephone)[1]
            connection=Connection.objects.create(identity=str(sheet.cell(row, telephone_col)),
                                                                    backend=backend)
            connection.contact=contact
            connection.save()
        return contact
    except:
        return None

def parse_status(row,worksheet,cols):
    return worksheet.cell(row, cols['status']).value

def parse_consignee(row,worksheet,cols):
    return Contact.objects.filter(name__icontains = worksheet.cell(row, cols['consignee']).value)[0]

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
        duplicates=[]
        for row in range(worksheet.nrows)[1:]:

            try:
                #check if delivery exists
                d=Delivery.objects.get(waybill=parse_waybill(row,worksheet,cols))
                duplicates.append(d.waybill)

            except Delivery.DoesNotExist:
                delivery=Delivery.objects.create(waybill=parse_waybill(row,worksheet,cols),
                                                       date_shipped=parse_date_shipped(row,worksheet,cols) ,
                                                       consignee=parse_consignee(row,worksheet,cols),
                                                       transporter=parse_transporter(row,worksheet,cols))
                deliveries.append(delivery.waybill)
                continue
        if len(deliveries)>0:
            return 'deliveries with waybills ' +' ,'.join(deliveries) + " have been uploaded !\n"
        elif len(duplicates )>0:
            return "it seems you have uploaded a duplicate excel file !!!"
        else:
            return "you seem to have uploaded an empty excel file..."
    else:
        return "Invalid file"



def index(request):
    if request.method == 'POST':
        deliveryform = UploadForm(request.POST, request.FILES)
        consigneeform=ConsigneeForm(request.POST, request.FILES)
        if deliveryform.is_valid() or consigneeform.is_valid():
            if deliveryform.is_valid() and deliveryform.cleaned_data.get('nodelivery', False):
                ##increase the script session for admin retry by 1 day
                admins=ScriptSession.objects.all()
            else:

                if deliveryform.is_valid() and request.FILES.get('excel_file',None):
                    message= handle_excel_file(request.FILES['excel_file'])
                if consigneeform.is_valid() and request.FILES.get('consignee_file',None):
                    message= load_excel_file(request.FILES['consignee_file'], 'consignee')
                return render_to_response('supplytracking/index.html', {'deliveryform':deliveryform,'consigneeform':consigneeform,'message':message}, context_instance=RequestContext(request))

    deliveryform = UploadForm()
    consigneeform=ConsigneeForm()
    return render_to_response('supplytracking/index.html', {'deliveryform':deliveryform,'consigneeform':consigneeform}, context_instance=RequestContext(request))
