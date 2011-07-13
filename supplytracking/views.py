from django.shortcuts import render_to_response
from django.template import RequestContext
from django import forms
from django.forms.util import ErrorList
from django.db import IntegrityError

from xlrd import open_workbook
from uganda_common.utils import assign_backend
from supplytracking.models import *
import datetime
from script.models import *
from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import HttpRouter
from rapidsms.models import Connection
from django.views.decorators.cache import cache_control
from django.contrib.auth.decorators import login_required
from ureport.views import handle_excel_file as upload_excel

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
    fields=['waybill nr', 'transporter','consignee','shipping date']
    field_cols={}
    for col in range(worksheet.ncols):
        value = worksheet.cell(0, col).value

        for field in fields:
            if value.lower().find(field) >= 0:
                field_cols[field]=col
    return field_cols


def parse_waybill(row,worksheet,cols):
    return str(worksheet.cell(row, cols['waybill nr']).value).strip()

def parse_transporter(row,worksheet,cols):
    try:
        name=str(worksheet.cell(row, cols['transporter']).value).strip()
        name = ' '.join([t.capitalize() for t in name.lower().split()])
#        contact,contact_created=Contact.objects.get_or_create(name=str(worksheet.cell(row, cols['transporter']).value).lower())
        contact,contact_created=Contact.objects.get_or_create(name__iexact=name)
        if contact_created:
            group,group_created=Group.objects.get_or_create(name='transporter')
            contact.groups.add(group)
        return contact
    except:
        return None

def parse_status(row,worksheet,cols):
    return str(worksheet.cell(row, cols['status']).value)

def parse_consignee(row,worksheet,cols):
    name=str(worksheet.cell(row, cols['consignee']).value).strip()
    name = ' '.join([t.capitalize() for t in name.lower().split()])
    try:
        return Contact.objects.get(name__iexact=name)
    except Contact.DoesNotExist:
        return 'Consignee:--> '+name+' <-- does not exist in the system, please first upload the consignee details before uploading deliveries to this consignee'

def parse_date_shipped(row,worksheet,cols):
    try:
        date = datetime.datetime.strptime(str(worksheet.cell(row, cols['shipping date']).value).lower(),'%d/%m/%Y')
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
                if type(parse_consignee(row, worksheet, cols)) == Contact:
                    delivery=Delivery.objects.create(waybill=parse_waybill(row,worksheet,cols).upper(),
                                                           date_shipped=parse_date_shipped(row,worksheet,cols) ,
                                                           consignee=parse_consignee(row,worksheet,cols),
                                                           transporter=parse_transporter(row,worksheet,cols))
                    
                    #if delivery's consignee and connection are not in any scriptprogress, dump them there
                    if not ScriptProgress.objects.filter(connection=delivery.consignee.default_connection).exists():
                        consignee_progress=ScriptProgress.objects.create(script=Script.objects.get(slug="consignee"),\
                                                                          connection=delivery.consignee.default_connection)
                    else:
                        #dump it in the backlog
                        DeliveryBackLog.objects.create(delivery=delivery)
                    
                    #create transporter scriptprogress if transporter does not exist in the scriptprogress model
                    if delivery.transporter.default_connection:
                        if not ScriptProgress.objects.filter(connection=delivery.transporter.default_connection).exists():
                            transporter_progress=ScriptProgress.objects.create(script=Script.objects.get(slug="transporter"),\
                                                                               connection=delivery.transporter.default_connection)
                    
                    #notify consignee of consignments
                    rounter = HttpRouter()
                    if delivery.consignee:
                        Message.objects.create(connection=Connection.objects.get(identity=delivery.consignee.default_connection.identity),
                                             text="Consignment " + str(delivery.waybill)+ " has been  sent ! ",
                                             direction='O',
                                             status='Q')
                    deliveries.append(delivery.waybill)               
                    continue
                else:
                    return parse_consignee(row, worksheet, cols)
                    exit()
        if len(deliveries)>0:
            return 'deliveries with waybills ' +' ,'.join(deliveries) + " have been uploaded !\n"
        elif len(duplicates )>0:
            return "it seems you have uploaded a duplicate excel file !!!"
        else:
            return "you seem to have uploaded an empty excel file..."
    else:
        return "Invalid file"


@login_required
@cache_control(no_cache=True, max_age=0)
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
                    group, created = Group.objects.get_or_create(name='consignee')
                    fields = ['name', 'telephone']
                    message = upload_excel(request.FILES['consignee_file'], group, fields)
#                    message= load_excel_file(request.FILES['consignee_file'], 'consignee')
                if transporterform.is_valid() and request.FILES.get('transporter_file',None):
                    group, created = Group.objects.get_or_create(name='transporter')
                    fields = ['company name', 'telephone']
                    message = upload_excel(request.FILES['transporter_file'], group, fields)
#                    message= load_excel_file(request.FILES['transporter_file'], 'transporter')
                return render_to_response('supplytracking/index.html', 
                                          {'deliveryform':deliveryform,
                                           'transporterform':transporterform,
                                           'consigneeform':consigneeform,
                                           'message':message
                                           }, context_instance=RequestContext(request))

    deliveryform = UploadForm()
    consigneeform=ConsigneeForm()
    transporterform=TransporterForm()
    return render_to_response('supplytracking/index.html', {
                                                            'deliveryform':deliveryform,
                                                            'transporterform':transporterform,
                                                            'consigneeform':consigneeform,
                                                            }, context_instance=RequestContext(request))
@login_required
@cache_control(no_cache=True, max_age=0)
def view_deliveries(request):
    deliveries=Delivery.objects.all()
    return render_to_response('supplytracking/deliveries.html',{'deliveries':deliveries},context_instance=RequestContext(request))

@login_required
@cache_control(no_cache=True, max_age=0)
def view_consignees(request):
    consignees=Contact.objects.filter(groups__in=[Group.objects.get(name='consignee')])
    return render_to_response('supplytracking/consignees.html',{'consignees':consignees},context_instance=RequestContext(request))

@login_required
@cache_control(no_cache=True, max_age=0)
def view_transporters(request):
    transporters=Contact.objects.filter(groups__in=[Group.objects.get(name='transporter')])
    return render_to_response('supplytracking/transporters.html',{'transporters':transporters},context_instance=RequestContext(request))
