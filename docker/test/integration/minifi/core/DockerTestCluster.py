import json
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid

from .SingleNodeDockerCluster import SingleNodeDockerCluster
from .utils import retry_check
from .FileSystemObserver import FileSystemObserver

class DockerTestCluster(SingleNodeDockerCluster):
    def __init__(self):
        self.segfault = False

        super(DockerTestCluster, self).__init__()

    def deploy_flow(self):

        super(DockerTestCluster, self).deploy_flow()

    def start_flow(self, name):
        container = self.containers[name]
        container.reload()
        logging.info("Status before start: %s", container.status)
        if container.status == 'exited':
            logging.info("Start container: %s", name)
            container.start()
            return True
        return False

    def stop_flow(self, name):
        container = self.containers[name]
        container.reload()
        logging.info("Status before stop: %s", container.status)
        if container.status == 'running':
            logging.info("Stop container: %s", name)
            container.stop(timeout=0)
            return True
        return False

    def get_app_log(self):
        for container in self.containers.values():
            container = self.client.containers.get(container.id)
            if b'Segmentation fault' in container.logs():
                logging.warn('Container segfaulted: %s', container.name)
                self.segfault=True
            if container.status == 'running':
                apps = [("MiNiFi", self.minifi_root + '/logs/minifi-app.log'), ("NiFi", self.nifi_root + '/logs/nifi-app.log'), ("Kafka", self.kafka_broker_root + '/logs/server.log')]
                for app in apps:
                    app_log_status, app_log = container.exec_run('/bin/sh -c \'cat ' + app[1] + '\'')
                    if app_log_status == 0:
                        logging.info('%s app logs for container \'%s\':\n', app[0], container.name)
                        return app_log
                        break
                else:
                    logging.warning("The container is running, but none of %s logs were found", " or ".join([x[0] for x in apps]))
            else:
                logging.info(container.status)
                logging.info('Could not cat app logs for container \'%s\' because it is not running', container.name)
        return None

    def wait_for_app_logs(self, log, timeout_seconds, count=1):
        wait_start_time = time.perf_counter()
        for container_name, container in self.containers.items():
            logging.info('Waiting for app-logs `%s` in container `%s`', log, container_name)
            while (time.perf_counter() - wait_start_time) < timeout_seconds:
                logs = self.get_app_log()
                if logs is not None and count <= logs.decode("utf-8").count(log):
                    return True
                if logs is not None:
                    for line in logs.decode("utf-8").splitlines():
                        logging.info("App-log: %s", line)
                time.sleep(1)
        return False

    def log_nifi_output(self):
        app_log = self.get_app_log()
        if app_log is None:
            return
        for line in app_log.decode("utf-8").splitlines():
            logging.info(line)

    def check_minifi_container_started(self):
        for container in self.containers.values():
            container = self.client.containers.get(container.id)
            if b'Segmentation fault' in container.logs():
                logging.warn('Container segfaulted: %s', container.name)
                raise Exception("Container failed to start up.")

    def check_http_proxy_access(self, url):
        output = subprocess.check_output(["docker", "exec", "http-proxy", "cat", "/var/log/squid/access.log"]).decode(sys.stdout.encoding)
        return url in output and \
            ((output.count("TCP_DENIED/407") != 0 and \
              output.count("TCP_MISS/200") == output.count("TCP_DENIED/407")) or \
             output.count("TCP_DENIED/407") == 0 and "TCP_MISS" in output)

    @retry_check()
    def check_s3_server_object_data(self, test_data):
        s3_mock_dir = subprocess.check_output(["docker", "exec", "s3-server", "find", "/tmp/", "-type", "d", "-name", "s3mock*"]).decode(sys.stdout.encoding).strip()
        file_data = subprocess.check_output(["docker", "exec", "s3-server", "cat", s3_mock_dir + "/test_bucket/test_object_key/fileData"]).decode(sys.stdout.encoding)
        return file_data == test_data

    @retry_check()
    def check_s3_server_object_metadata(self, content_type="application/octet-stream", metadata=dict()):
        s3_mock_dir = subprocess.check_output(["docker", "exec", "s3-server", "find", "/tmp/", "-type", "d", "-name", "s3mock*"]).decode(sys.stdout.encoding).strip()
        metadata_json = subprocess.check_output(["docker", "exec", "s3-server", "cat", s3_mock_dir + "/test_bucket/test_object_key/metadata"]).decode(sys.stdout.encoding)
        server_metadata = json.loads(metadata_json)
        return server_metadata["contentType"] == content_type and metadata == server_metadata["userMetadata"]

    @retry_check()
    def is_s3_bucket_empty(self):
        s3_mock_dir = subprocess.check_output(["docker", "exec", "s3-server", "find", "/tmp/", "-type", "d", "-name", "s3mock*"]).decode(sys.stdout.encoding).strip()
        ls_result = subprocess.check_output(["docker", "exec", "s3-server", "ls", s3_mock_dir + "/test_bucket/"]).decode(sys.stdout.encoding)
        return not ls_result

    def wait_for_container_logs(self, container_name, log, timeout, count=1):
        logging.info('Waiting for logs `%s` in container `%s`', log, container_name)
        container = self.containers[container_name]
        check_count = 0
        while check_count <= timeout:
            if count <= container.logs().decode("utf-8").count(log):
                return True
            else:
                check_count += 1
                time.sleep(1)
        return False

    def segfault_happened(self):
        return self.segfault
