import requests
from requests.auth import HTTPBasicAuth
from socket import error as SocketError
import json
import datetime
TIMEOUT = 4  # seconds


# These are the values we need in @plugin_specific_extra_args
# "kibana.URL", "kibana.USER", "kibana.PASSWORD", "kibana.APPS"
def compute_metrics(plugin_specific_extra_args, interval_in_minutes):
    base_url = plugin_specific_extra_args.get("%s.URL" % __name__, "")
    user = plugin_specific_extra_args.get("%s.USER" % __name__, "")
    password = plugin_specific_extra_args.get("%s.PASSWORD" % __name__, "")
    app_names = plugin_specific_extra_args.get("%s.APPS" % __name__, "").split(",")
    if len(app_names) == 0:
        raise ValueError("No Apps found under the parameters provided: %s" % app_names)
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(minutes=interval_in_minutes)
    result = []
    for app_name in app_names:
        metrics = _get_app_instance_metrics(base_url, user, password, app_name, start_time, end_time)
        result.extend(metrics)
    return result


def _extract_cpu_usage_from_series(series_array):
    result = 0.0
    for series in series_array:
        if series["key"] == "processCPUMax":
            result = series["overallValue"]
    return result * 100 if result is not None else 0  # *100 to percentage as 0...100


def _extract_memory_usage_from_series(series_array):
    result = 0.0
    for series in series_array:
        if series["key"] == "memoryUsedMax":
            result = series["overallValue"]
    return result * 1024 * 1024 * 1024 if result is not None else 0  # from float GB to bytes


def _extract_memory_and_cpu_usage_from_charts_data(charts_dict):
    charts = charts_dict["charts"]
    cpu_usage = 0.0
    mem_usage = 0.0
    for chart in charts:
        if chart["key"] == "cpu_usage_chart":
            cpu_usage = _extract_cpu_usage_from_series(chart["series"])
        if chart["key"] == "memory_usage_chart":
            mem_usage = _extract_memory_usage_from_series(chart["series"])
    return [cpu_usage, mem_usage]


def _extract_agent_rpm_epm_from_requests_data(perf_data_dict):
    perf_data = perf_data_dict["items"]
    if len(perf_data) <= 0:
        return ["", 0, 0]
    perf_data = perf_data[0]
    return [perf_data["agentName"], perf_data["transactionsPerMinute"], perf_data["errorsPerMinute"]]


def _extract_container_ids(filter_response_list):
    result = []
    for data_dict in filter_response_list:
        if data_dict["name"] == "containerId":
            for option in data_dict["options"]:
                result.append(option["name"])
    return result


def _get_app_instance_metrics(base_url, user, password, app_name, start_time, end_time):
    result = []
    url = r'%s/s/apm/api/apm/ui_filters/local_filters/metrics?start=%sZ&end=%sZ&uiFilters={}&filterNames=["host","containerId","podName"]&serviceName=%s' % (base_url, start_time.isoformat(), end_time.isoformat(), app_name)
    request_containers_response = connect_and_get(url, user, password)
    if not request_containers_response.ok:
        raise ValueError("Response error opening %s" % url)
    request_containers_response_dict = json.loads(request_containers_response.content)
    container_ids = _extract_container_ids(request_containers_response_dict)

    for container_id in container_ids:
        url = r'%s/s/apm/api/apm/services?start=%s&end=%s&uiFilters={"kuery":"transaction.type : \"request\" and container.id : \"%s\""}' % (base_url, start_time.isoformat(), end_time.isoformat(), container_id)
        request_performance_response = connect_and_get(url, user, password)
        if not request_performance_response.ok:
            raise ValueError("Response error opening %s" % url)
        request_performance_dict = json.loads(request_performance_response.content)
        agent, rpm, epm = _extract_agent_rpm_epm_from_requests_data(request_performance_dict)

        url = r'%s/s/apm/api/apm/services/%s/metrics/charts?start=%sZ&end=%sZ&agentName=%s&uiFilters={"containerId":["%s"]}' % (base_url, app_name, start_time.isoformat(), end_time.isoformat(), agent, container_id)
        charts_response = connect_and_get(url, user, password)
        if not charts_response.ok:
            raise ValueError("Response error opening %s" % url)
        charts_dict = json.loads(charts_response.content)
        cpu, memory = _extract_memory_and_cpu_usage_from_charts_data(charts_dict)

        url = r'%s/s/apm/api/apm/services/%s/transaction_groups?start=%sZ&end=%sZ&transactionType=request&uiFilters={"containerId":["%s"]}' % (base_url, app_name, start_time.isoformat(), end_time.isoformat(), container_id)
        transations_response = connect_and_get(url, user, password)
        if not transations_response.ok:
            raise ValueError("Response error opening %s" % url)
        transations_list = json.loads(transations_response.content)

        result.append({"mem": int(memory),
                       "endpoints": len(transations_list),
                       "apdex": 0,  # TODO APDEX implemented by hand via scripted field: https://discuss.elastic.co/t/kibana-calculate-apdex-with-value-from-scripted-field/149845/11
                       "cpu": float(cpu),
                       "rpm": float(rpm),
                       "epm": float(epm),
                       "_lang": agent,
                       "_appname": app_name})

    return result


def connect_and_get(url, user, password, verify=True, timeout=TIMEOUT):
    auth = HTTPBasicAuth(user, password)
    return _get(url, auth, verify=verify, timeout=timeout)


def _get(url, auth, verify=True, timeout=TIMEOUT):
    try:
        return requests.get(url, auth=auth, verify=verify, timeout=timeout)
    except requests.exceptions.ConnectionError:
        raise ValueError("Connection error opening %s" % url)
    except SocketError:
        raise ValueError("Socket error opening %s" % url)
    except requests.exceptions.ReadTimeout:
        raise ValueError("Read timeout opening %s" % url)
    except requests.exceptions.ChunkedEncodingError:
        raise ValueError("Encoding error opening %s" % url)