from django.shortcuts import render_to_response
from django.template import RequestContext
from django import forms

from xlrd import open_workbook
from datetime import datetime
import dateutil

class UploadForm(forms.Form):
    nodelivery=forms.BooleanField(widget=forms.CheckboxInput(),
                             label='No delivery',required=False)
    excel_file = forms.FileField(label="Excel File")


def handle_excel_file(file):
    if file:
        excel=file.read()
        workbook=open_workbook(file_contents=excel)
        sheet = workbook.sheet_by_index(0)
        #iterate over the first row
        #and get the cell containing waybills
        way_bill_col=''
        consignee_col=''
        date_shipped_col=''

        for col in range(sheet.ncols):
            value=sheet.cell(0,col).value
            if value.find("waybill") >=0:
                way_bill_col=col
            if value.find("consignee") >=0:
                consignee_col=col
            if value.find("transporter") >=0:
                transporter_col=col
            if value.find("shipped") >=0 and value.find("date"):
                date_shipped_col=col

        #create delivery objects 
        for row in range(sheet.nrows):
            transporter_connection = Connection.objects.create(identity=sheet.cell(row,transporter_col), backend=test_backend)
            consignee_connection = Connection.objects.create(identity=sheet.cell(row,consignee_col), backend=test_backend)
            delivery=Delivery.objects.create(waybill=sheet.cell(row,way_bill_col), date_shipped=dateutil.parser.parse(sheet.cell(row,date_shipped_col).value), consignee=consignee_connection,
                                           transporter=transporter_connection)
        user = User.objects.get(username="admin")
        tranporter_script = Script.objects.create(
                slug="transporter",
                name="transporter script",
        )

        delivery_poll=Poll.create_yesno('consignment_delivered', 'Has the consignment been delivered?', [], user)
        transporter_script.steps.add(ScriptStep.objects.create(
            script=transporter_script,
            poll=delivery_poll,
            order=0,
            rule=ScriptStep.STRICT,
            start_offset=3600*24*3,
            rentry_offset=3600*24,
            ))


        ###  consignee script ####

        consignee_script = Script.objects.create(
                slug="consignee",
                name="script for consignee",
        )

        consignee_script.steps.add(ScriptStep.objects.create(
            script=admin_consignee_script,
            message='consignment sent !',
            order=0,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=0,
            giveup_offset=3600*24*3,
            ))

        consignee_script.steps.add(ScriptStep.objects.create(
            script=consignee_script,
            poll=delivery_poll,
            order=1,
            rule=ScriptStep.STRICT,
            start_offset=0,
            rentry_offset=3600*24,
            ))



def index(request):
    if request.method == 'POST':
            a=request.POST
            form = UploadForm(request.POST, request.FILES)
            if form.is_valid():
                parse_excel_file(request.FILES['excel_file'])
                return
        else:
            form = UploadForm()

    upload_form=UploadForm()
    return render_to_response('supplytracking/index.html',{'form':form},context_instance=RequestContext(request))