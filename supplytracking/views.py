from django.shortcuts import render_to_response
from django.template import RequestContext
from django import forms
from django.forms.util import ErrorList
from django.db import IntegrityError

from xlrd import open_workbook
from uganda_common.utils import assign_backend
import dateutil
from supplytracking.utils import load_excel_file
from supplytracking.models import *
import datetime
from script.models import *
from rapidsms_httprouter.router import get_router

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
class TransporterForm(forms.Form):
    transporter_file = forms.FileField(label="Transporters Excel File",required=False)
    def clean(self):
        excel = self.cleaned_data.get('transporter_file',None)
        if excel and excel.name.rsplit('.')[1] != 'xls':
                msg=u'Upload valid excel file !!!'
                self._errors["transporter_file"]=ErrorList([msg])
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
    return str(worksheet.cell(row, cols['waybill']).value).lower()

def parse_transporter(row,worksheet,cols):
    try:
        contact,contact_created=Contact.objects.get_or_create(name=str(worksheet.cell(row, cols['transporter']).value).lower())
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
    return str(worksheet.cell(row, cols['status']).value)

def parse_consignee(row,worksheet,cols):
    return Contact.objects.get(name = str(worksheet.cell(row, cols['consignee']).value).lower())

def parse_date_shipped(row,worksheet,cols):
    try:
        date=dateutil.parser.parse(str(worksheet.cell(row, cols['date_shipped']).value).lower())
    except:
        date=datetime.datetime.now().date()
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
                
                #if delivery's consignee and connection are not in any scriptprogress, dump them there
                if not ScriptProgress.objects.filter(connection=delivery.consignee.default_connection).exists() and not ScriptProgress.objects.filter(connection=delivery.transporter.default_connection).exists():
                    if delivery.transporter.default_connection:
                        transporter_progress=ScriptProgress.objects.create(script=Script.objects.get(slug="transporter"),
                                              connection=delivery.transporter.default_connection)
                    if delivery.consignee.default_connection:
                        consignee_progress=ScriptProgress.objects.create(script=Script.objects.get(slug="consignee"),
                                              connection=delivery.consignee.default_connection)
                else:
                    #dump it in the backlog
                    DeliveryBackLog.objects.create(delivery=delivery)

                router=get_router()
                if delivery.consignee:
                    router.add_outgoing(delivery.consignee.default_connection,"consignment" + str(delivery.waybill)+ "has been  sent ! ")
                
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
        transporterform=TransporterForm(request.POST, request.FILES)
        if deliveryform.is_valid() or consigneeform.is_valid() or transporterform.is_valid():
            if deliveryform.is_valid() and deliveryform.cleaned_data.get('nodelivery', False):
                ##increase the script session for admin retry by 1 day
                pass
            else:

                if deliveryform.is_valid() and request.FILES.get('excel_file',None):
                    message= handle_excel_file(request.FILES['excel_file'])
                if consigneeform.is_valid() and request.FILES.get('consignee_file',None):
                    message= load_excel_file(request.FILES['consignee_file'], 'consignee')
                if transporterform.is_valid() and request.FILES.get('transporter_file',None):
                    message= load_excel_file(request.FILES['transporter_file'], 'transporter')
                return render_to_response('supplytracking/index.html', {'deliveryform':deliveryform,'transporterform':transporterform,'consigneeform':consigneeform,'message':message}, context_instance=RequestContext(request))

    deliveryform = UploadForm()
    consigneeform=ConsigneeForm()
    transporterform=TransporterForm()
    return render_to_response('supplytracking/index.html', {'deliveryform':deliveryform,'transporterform':transporterform,'consigneeform':consigneeform}, context_instance=RequestContext(request))
