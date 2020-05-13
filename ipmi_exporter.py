import subprocess
import itertools
import time
import logging
import os
from multiprocessing import Process, Manager
from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, REGISTRY


try:
    IPS = os.getenv('TARGET_IPS').split(',')
except AttributeError:
    raise Exception("Mandatory `TARGET_IPS` environment variable is not set")

IPMI_USER = os.getenv('IPMI_USER', 'ADMIN')
IPMI_PASSWD = os.getenv('IPMI_PASSWD', 'ADMIN')

REQURED = [
    "CPU Temp",
    "System Temp",
    "Peripheral Temp",
    "MB_10G Temp",
    "DIMMA1 Temp",
    "FAN1",
    "FAN2",
    "FAN3",
    "FAN4",
]
# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')


def _run_cmd(ip, raw):
    logging.info("Collecting from target %s", ip)
    proc = subprocess.Popen(["ipmitool",
                             "-H", ip,
                             "-U", IPMI_USER,
                             "-P", IPMI_PASSWD,
                             "sdr"], stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    raw += [x.rstrip() for x in out.split('|')]


class IpmiCollector(object):
    @REQUEST_TIME.time()
    def collect(self):
        sys_metrics = {
            'cpu_temp': GaugeMetricFamily('ipmi_cpu_temp', 'CPU temp', labels=['ip']),
            'system_temp': GaugeMetricFamily('ipmi_system_temp', 'System temp', labels=['ip']),
            'peripheral_temp': GaugeMetricFamily('ipmi_peripheral_temp', 'Peripheral temp', labels=['ip']),
            '10g_temp': GaugeMetricFamily('ipmi_10g_temp', '10G temp', labels=['ip']),
            'ram_temp': GaugeMetricFamily('ipmi_ram_temp', 'RAM temp', labels=['ip']),
            'fan1_speed': GaugeMetricFamily('ipmi_fan_speed', 'Fan1 speed', labels=['ip']),
            'fan2_speed': GaugeMetricFamily('ipmi_fan_speed', 'Fan2 speed', labels=['ip']),
            'fan3_speed': GaugeMetricFamily('ipmi_fan_speed', 'Fan3 speed', labels=['ip']),
            'fan4_speed': GaugeMetricFamily('ipmi_fan_speed', 'Fan4 speed', labels=['ip']),
            'volt': GaugeMetricFamily('ipmi_volt', 'Volt', labels=['ip'])
        }
        raw = Manager().list([])
        for ip in IPS:
            # This is an attempt to run the `ipmi` tool in parallel
            # to avoid timeouts in Prometheus
            p = Process(target=_run_cmd, args=(ip, raw))
            logging.info("Start collecting the metrics")
            p.start()
            p.join()
            all_metrics = dict(itertools.izip_longest(*[iter(raw)] * 2, fillvalue=""))
            for k, v in all_metrics.items():
                for r in REQURED:
                    if r in k:
                        value = [int(s) for s in v.split() if s.isdigit()][0]
                        if 'CPU' in k:
                            sys_metrics['cpu_temp'].add_metric([ip], value)
                        elif 'System' in k:
                            sys_metrics['system_temp'].add_metric([ip], value)
                        elif 'Peripheral' in k:
                            sys_metrics['peripheral_temp'].add_metric([ip], value)
                        elif 'MB_10G' in k:
                            sys_metrics['10g_temp'].add_metric([ip], value)
                        elif 'DIMMA1' in k:
                            sys_metrics['ram_temp'].add_metric([ip], value)
                        elif 'FAN1' in k:
                            sys_metrics['fan1_speed'].add_metric([ip], value)
                        elif 'FAN2' in k:
                            sys_metrics['fan2_speed'].add_metric([ip], value)
                        elif 'FAN3' in k:
                            sys_metrics['fan3_speed'].add_metric([ip], value)
                        elif 'FAN4' in k:
                            sys_metrics['fan4_speed'].add_metric([ip], value)
                        else:
                            logging.error("Undefined metric: %s", k)

        for metric in sys_metrics.values():
            yield metric


def main():
    REGISTRY.register(IpmiCollector())
    start_http_server(8000)
    while True:
        time.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(format='ts=%(asctime)s level=%(levelname)s msg=%(message)s', level=logging.DEBUG)
    main()
