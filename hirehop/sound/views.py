from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django import forms


import yaml
import json
import requests
from urllib.parse import urlencode

from .models import channel_lists, channel_list_input, channel_list_output
from .forms import ChannelListsForm, ChannelListInputForm

#Logging to a speciefied file
import logging
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                    filename='/app/logs/sound.log', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')


#Open configuration file
with open('/app/hirehopScanning/config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

api_token = config['hirehop']['api_token']

def add_equipment(request, job_nr, id):
    url = "https://myhirehop.com/api/save_job.php?token={}".format(api_token)

    payload = {
        'job': job_nr,
        "items": {"b{}".format(id):1}
    }

    payload = json.dumps(payload)


    headers = {}

    response = requests.request("POST", url, headers=headers, data=payload)

    #messages.info(request, response.text)

    mixer = json.loads(response.text)['items']['itms']

    inputs = mixer[0]['CUSTOM_FIELDS']['inputs']['value']
    outputs = mixer[0]['CUSTOM_FIELDS']['outputs']['value']

    #messages.info(request, "Inputs: {} - Outputs: {}".format(inputs, outputs))

    return mixer

def get_job_data(request, job_nr):
    url = "https://myhirehop.com/api/job_data.php?token={}&job={}".format(api_token, job_nr)

    payload={}
    headers={}

    response = requests.request("GET", url, headers=headers, data=payload)

    job = json.loads(response.text)
    return job



def create_channellist_function(request, channellist_name, project_id, mixer_id, mixer):
    # create a channel_lists item
    channel_list = channel_lists.objects.create(Name=channellist_name, projectID=project_id, mixerID=mixer_id)


    inputs = int(mixer[0]['CUSTOM_FIELDS']['inputs']['value'])
    outputs = int(mixer[0]['CUSTOM_FIELDS']['outputs']['value'])

    # create channel_list_inputs
    for i in range(inputs):
        channel_list_input_1 = channel_list_input.objects.create(channel_list=channel_list, musician="Musician", 
                                                                notes="", instrument="Instrument",
                                                                stage_input="{}".format(i+1), console_channel=i+1, 
                                                                mic_di="", phantom_power=False)

    # create channel_list_outputs
    for i in range(outputs):
        channel_list_output_1 = channel_list_output.objects.create(channel_list=channel_list, instrument="Instrument",
                                                                person="Person", output_type="Output Type",
                                                                console_output=i+1, notes="Output notes", mix="Mix {}".format(i+1))



@login_required
def index(request):
    job_nr = request.GET.get('job', '')
    channel_list_id = request.GET.get('channel_list', '')
    action = request.GET.get('action', '')


    channel_lists_dict = channel_lists.objects.filter(projectID=job_nr).values()
    channel_lists_list = list(channel_lists_dict)

    log_message = "Channellists: {}".format(channel_lists_list)

    if action == 'delete':
        channel_lists.objects.filter(ID=channel_list_id).delete()
        channel_lists_dict = channel_lists.objects.filter(projectID=job_nr).values()
        channel_lists_list = list(channel_lists_dict)

    if action == 'new' or not channel_lists_list:

        parameters = {'job': job_nr}
        # build the URL with the parameters and redirect
        url = '/sound/create_channellist?' + urlencode(parameters)
        return redirect(url)

    logging.info(log_message)


    #Render index page
    return render(request, 'sound/index.html', {'channel_lists': channel_lists_list, 'job': job_nr})

@login_required
def create_channellist(request):
    job_nr = request.GET.get('job', '')

    logging.info('Create new channellist')

    form = ChannelListsForm(initial={'projectID': job_nr})

    #If there is a POST-request
    if request.method == 'POST':
        form = ChannelListsForm(request.POST)
        #Check if form is valid
        if form.is_valid():
            cd = form.cleaned_data
            #update channellist with the form data
            logging.info(cd)

            #messages.info(request, cd)

            mixer = add_equipment(request, cd.get('projectID'), cd.get('mixerID'))

            create_channellist_function(request, cd.get('Name'), cd.get('projectID'), cd.get('mixerID'), mixer)

            #Update the page
            parameters = {'job': job_nr}
            # build the URL with the parameters and redirect
            url = '/sound/?' + urlencode(parameters)
            return redirect(url)
        else:
            #If the form data is corupt it will show a message but since the form is only a optinon list and the options are always valid it shouldn´t happen
            messages.error(request, 'This shouldnt be able to happen...')
    #Before any POST-action render the page from this template

    #Render index page
    return render(request, 'sound/create_channellist.html', {'job': job_nr, 'form': form})


@login_required
def edit_channellist(request):
    job_nr = request.GET.get('job', '')
    channel_list_ID = request.GET.get('channel_list', '')

    job = get_job_data(request, job_nr)

    channel_lists_obj = get_object_or_404(channel_lists, ID=channel_list_ID)
    channel_list_inputs = channel_list_input.objects.filter(channel_list=channel_list_ID).order_by('console_channel')

    ChannelListInputFormSet = forms.modelformset_factory(channel_list_input, form=ChannelListInputForm, extra=0)
    formset = ChannelListInputFormSet(queryset=channel_list_inputs)

    logging.info('Edit channellist')

    if request.method == 'POST':
    form_identifier = request.POST.get('form_identifier', '')
    if form_identifier == "ChannelListInputForm":
        # Update channel_list_input data
        form = ChannelListInputForm(request.POST, instance=channel_list_input_obj)
        if form.is_valid():
            form.save()
            return redirect('/sound/channellist?channel_list={}&action=edit&job={}'.format(channel_list_ID, job_nr))
    else:
        # Update channel_lists data
        form = ChannelListsForm(request.POST, instance=channel_lists_obj)
        formset = ChannelListInputFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            form.save()
            instances = formset.save()
            return redirect('/sound/channellist?channel_list={}&action=edit&job={}'.format(channel_list_ID, job_nr))
        else:
            messages.error(request, 'Form data is not valid.')
else:
    # Display the forms
    form = ChannelListInputForm(instance=channel_list_input_obj)
    formset = ChannelListInputFormSet(queryset=channel_list_inputs)
    form = ChannelListsForm(instance=channel_lists_obj)


    return render(request, 'sound/edit_channellist.html', {'job': job_nr, 'form': form, 'job_data': job, 'formset': formset})



@login_required
def channel_list_input_update(request, pk):
    job_nr = request.GET.get('job', '')
    channel_list_ID = request.GET.get('channel_list', '')
    channel_list_input_obj = get_object_or_404(channel_list_input, pk=pk)
    if request.method == 'POST':
        form = ChannelListInputForm(request.POST, instance=channel_list_input_obj)
        if form.is_valid():
            form.save()
            return redirect('/sound/channellist?channel_list={}&action=edit&job={}'.format(channel_list_ID, job_nr))
    else:
        form = ChannelListInputForm(instance=channel_list_input_obj)
        messages.warning(request, 'Request type not POST')
    return redirect('/sound/channellist?channel_list={}&action=edit&job={}'.format(channel_list_ID, job_nr))
