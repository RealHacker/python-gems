from django.shortcuts import render
from models import *
from django.http import HttpResponse, HttpResponseRedirect
import json
import re
import urlparse

tpl_404 ="""
<html>
    <head>
        <title>404 not found</title>
    </head>
    <body>
        <h1>404 - Not Found</h1><hr>
        <h2>%s</h2>
    </body>
</html>
"""
def mock_server_error(msg):
    json_msg = json.dumps({"msg": msg})
    return HttpResponse(json_msg, status=500, content_type="application/json")

def mock_server_success():
    return HttpResponse("OK", status=200)

def mock_server_404(msg):
    page_404 = tpl_404%msg
    return HttpResponse(page_404, status=404)

def index(request):
    """ The main page for application """
    return render(request, "index.html")

def states(request):
    # CRUD for global states
    if request.method=="GET":
        states = GlobalState.objects.values()
        states_json = json.dumps(states)
        return HttpResponse(states_json, content_type="application/json")
    else:
        try:
            payload = json.loads(request.body)
        except:
            return mock_server_error("Fail to unmarshal json string")
        if request.method=="POST":
            # add a new state
            required = ["name", "value", "type"]
            for field in required:
                if field not in payload:
                    return mock_server_error("Lacking required field: %s"%field)
            if payload['type']=="boolean":
                if payload['value'] not in ['true', 'false']:
                    return mock_server_error("Invalid value for boolean state")
                
            new_state = GlobalState(name=payload['name'],
                    value=payload['value'], statetype=payload['type'])
            new_state.save()
            return mock_server_success()
        elif request.method=="PUT":
            required = ["name", "value"]
            for field in required:
                if field not in payload:
                    return mock_server_error("Lacking required field: %s"%field)
            try:
                state = GlobalState.objects.get(name=payload['name'])
            except:
                return mock_server_error("Fail to get global state: %s"%payload['name'])
            
            if state.statetype=="boolean":
                if payload['value'] not in ['true', 'false']:
                    return mock_server_error("Invalid value for boolean state")
            state.value = payload['value']
            state.save()
            return mock_server_success()
        elif request.method=="DELETE":
            if "name" not in payload:
                return mock_server_error("Lacking required field: name")
            try:
                state = GlobalState.objects.get(name=payload['name'])
            except:
                return mock_server_error("Fail to get global state: %s"%payload['name'])
            state.delete()
            return mock_server_success()
        else:
            return mock_server_error("HTTP method not supported.")
        
def proxy(request):
    proxy = Proxy.objects.all()
    if request.method=="GET":
        result = {
            "isOn": False,
            "proxyserver": None
        }
        if proxy and proxy[0].isOn:
            result["isOn"]=True
            result["proxyserver"]=proxy.proxy_server
        result_json = json.dumps(result)
        return HttpResponse(result_json, content_type="application/json")
    elif request.method=="POST":
        try:
            payload = json.loads(request.body)
        except:
            return mock_server_error("Fail to unmarshal json string")
        if "isOn" not in payload:
            return mock_server_error("Lacking required field: isOn")
        if payload['isOn']=="true" and "proxyserver" not in payload:
            return mock_server_error("Lacking required field: proxyserver")
        if not proxy:
            p = Proxy()
        else:
            p = proxy[0]
        proxy.isOn = payload['isOn']
        proxy.proxy_server = payload['proxyserver']
        proxy.save()
        return mock_server_success()
    else:
        return mock_server_error("HTTP method not supported.")

def urls(request):
    if request.method=="GET":
        urls = list(URL.objects.values())
        urls_json = json.dumps(urls)
        return HttpResponse(urls_json, content_type="application/json")
    elif request.method=="POST":
        try:
            payload = json.loads(request.body)
        except:
            return mock_server_error("Fail to unmarshal json string")
        if "name" not in payload or "pattern" not in payload:
            return mock_server_error("Lacking required field") 
        try:
            re.compile(payload['pattern'])
        except:
            return mock_server_error("invalid regular expression")
        url = URL(name=payload['name'], pattern=payload['pattern'])
        url.save()
        return mock_server_success()
    elif request.method=="DELETE":
        try:
            payload = json.loads(request.body)
        except:
            return mock_server_error("Fail to unmarshal json string")
        if "id" not in payload:
            return mock_server_error("Lacking required field:id")
        try:
            url = URL.objects.get(id=int(payload['id']))
        except:
            return mock_server_error("URL not found")
        url.delete()
        return mock_server_success()
    else:
        return mock_server_error("HTTP method not supported.")
        
def conditions(request):
    if request.method=="GET":
        if "urlid" not in request.GET:
            return mock_server_error("Lacking required field: urlid")
        conditions = Condition.objects.filter(url_id=int(request.GET['urlid'])).values()
        json_conditions = json.dumps(conditions)
        return HttpResponse(json_conditions, content_type="application/json")
    elif request.method=="POST":
        # add a new condition, not supporting modification
        try:
            payload = json.loads(request.body)
        except:
            return mock_server_error("Fail to unmarshal json string")
        if "urlid" not in payload or "method" not in payload:
             return mock_server_error("Lacking required fields")
        try:
            url = URL.objects.get(id=int(payload['urlid']))
        except:
            return mock_server_error("URL not found")
        condition = Condition(url=url, method=payload['method'])
        if "state_filter" in payload:
            condition.state_filter = payload['state_filter']
        if "query_filter" in payload:
            condition.query_filter = payload['query_filter']
        condition.save()
        return mock_server_success()
    elif request.method=="DELETE":
        try:
            payload = json.loads(request.body)
        except:
            return mock_server_error("Fail to unmarshal json string")
        if "id" not in payload:
            return mock_server_error("Lacking required field: id")
        try:
            condition = Condition.objects.get(id=int(payload['id']))
        except:
            return mock_server_error("Condition not found")
        condition.delete()
        return mock_server_success()
    else:
       return mock_server_error("HTTP method not supported.") 
    
def responses(request):
    if request.method=="GET":
        if "conditionid" not in request.GET:
            return mock_server_error("Lacking required field: conditionid")
        try:
            response = Response.objects.get(condition_id=int(request.GET['conditionid'], is_inactive=False))
        except:
            return mock_server_error("Response not found")
        json_response = json.dumps({
            "id": response.id,
            "condition_id": response.condition_id,
            "response_type": response.response_type,
            "data": response.data,
            "status_code": response.status_code,
            "tpl_name": response.tpl_name,
            "tpl_type": response.tpl_type,
            "redirect_url": response.redirect_url,
        })
        return HttpResponse(json_response, content_type="application/json")
    elif request.method=="POST":
        try:
            payload = json.loads(request.body)
        except:
            return mock_server_error("Fail to unmarshal json string")
        if "conditionid" not in payload or "response_type" not in payload:
            return mock_server_error("Lacking required field: conditionid")
        try:
            condition = Condition.objects.get(id=int(payload['conditionid']))
        except:
            return mock_server_error("Condition not found")
        try:
            response = Response.objects.get(condition=condition)
        except:
            response = Response(condition=condition)
        response.response_type = payload['response_type']

        if "status_code" in payload:
            response.status_code = payload['status_code']
            if payload['status_code']/100==3: # redirect
                if "redirect_url" not in payload:
                    return mock_server_error("Lacking required field: redirect_url")
                response.redirect_url = payload['redirect_url']
                return mock_server_success()
        if "data" not in payload:
            return mock_server_error("Lacking required field: data")
        response.data = payload['data']
        
        if payload['response_type']==1:
            if "tpl_name" not in payload or "tpl_type" not in payload:
                return mock_server_error("Lacking required field: tpl_*")
            response.tpl_name = payload['tpl_name']
            response.tpl_type = payload['tpl_type']
        return mock_server_success()

# Handle the mocks    
def urlhandler(request):
    path = request.path
    # First try to match the path to a URL pattern
    urls = URL.objects.all()
    found = False
    for url in urls:
        mo = re.match(url.pattern, path)
        if mo:
            if mo.group(0)==path or (path[-1]=="/" and mo.group(0)==path[:-1]):
                found = True
                break
        elif url.pattern.endswith("/"):
            mo = re.match(url.pattern[:-1], path)
            if mo.group(0)==path:
                found = True
                break
    if not found:
        return mock_server_404("URL pattern not found")

    found = False
    # find matching condition
    states = GlobalState.objects.all()
    for condition in url.condition_set:
        # match method
        method_match = (condition.method == request.method)
        # match the global states
        if not condition.state_filter:
            state_match = True
        else:
            state_conds = condition.state_filter.split(",").strip()
            names = [cond.split("=")[0] for cond in state_conds]
            dicts = {cond.split("=")[0]:cond.split("=")[1] for cond in state_conds}
            state_match = True
            for state in states:
                if state.name not in names: continue
                if state.value != dicts[state.name]:
                    state_match = False
                    break
        # match the query
        if request.method!="GET" or not condition.query_filter:
            query_match = True
        else:
            query_match = True
            qs = urlparse.parse_qs(condition.query_filter)
            for key in qs:
                if key not in request.GET:
                    query_match = False
                    break
                if request.GET[key] not in qs[key]:
                    query_match = False
                    break
        if method_match and state_match and query_match:
            found = True
            break
    if not found:
        return mock_server_404("Request Condition not found")
    
    try:
        response = Response.objects.get(condition=condition)
    except:
        return mock_server_404("Response not define for this condition")

    # record the request in database
    record = AccessRecord(condition=condition, fullurl=path)
    record.save()
    
    # deliver the response
    if response.status_code/100==3 and response.redirect_url:
        return HttpResponseRedirect(response.redirect_url, status_code=response.status_code)

    status_code = response.status_code if response.status_code else 200

    if response.response_type==2: # json
        return HttpResponse(response.data, content_type="application/json", status_code=status_code)
    
    elif response.response_type==1:
        data = json.loads(response.data)
        if response.tpl_type=="django":
            return render(request, response.tpl_name, data, status_code=status_code)
        # jinja here
        else:
            return mock_server_error("Template engine not supported")

            
    
