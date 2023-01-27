from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from datetime import date

from office365.runtime.auth.client_credential import ClientCredential
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File

import yaml
import json

#Logging to a speciefied file
import logging
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                    filename='/app/logs/webhook.log', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

with open('/app/hirehopScanning/config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

api_token = config['hirehop']['api_token']

#Sharepoint config
sharepoint_user = config['sharepoint']['username']
sharepoint_password = config['sharepoint']['password']
sharepoint_client_id = config['sharepoint']['client_id']
sharepoint_client_secret = config['sharepoint']['client_secret']
sharepoint_site = config['sharepoint']['site']
sharepoint_library = config['sharepoint']['document_library']


# Authenticate to SharePoint
client_credentials = ClientCredential('{sharepoint_client_id}','{sharepoint_client_secret}')

# Connect to the SharePoint site
client = ClientContext(sharepoint_site).with_credentials(client_credentials)



@csrf_exempt
def new_job(request):
    if request.method == 'POST':
        data = request.POST.dict()
        data_raw = request.body
        data_json = json.loads(request.body)

        job_data = data_json['data']
        job_name = job_data['JOB_NAME']

        current_year = date.today().year

        create_sharepoint_folder = bool(job_data['CUSTOM_FIELDS']['sharepoint_project']['value'])

        if create_sharepoint_folder:
            #pass
            target_folder_url = "/{}/{}/{}".format(sharepoint_library, current_year, job_name)
            target_folder = client.web.ensure_folder_path(target_folder_url).execute_query()


            #folder = site.Folder('{}/{}/{}'.format(sharepoint_library, current_year, job_name))

        # process the webhook data here
        logging.info(data_json)
        print(create_sharepoint_folder)
        return JsonResponse({'status': 'success', 'data': data_json['data']})
    else:
        logging.info('No data')
        return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def invoice_created(request):
    if request.method == 'POST':
        data = request.POST.dict()
        data_raw = request.POST
        # process the webhook data here
        print(data)
        logging.info(data)
        logging.info(data_raw)
        return JsonResponse({'status': 'success'})
    else:
        logging.info('No data')
        return JsonResponse({'error': 'Invalid request method'})
