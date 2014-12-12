import json, os, subprocess
from boto.s3.connection import S3Connection
from boto.utils import get_instance_metadata
from boto.cloudformation import CloudFormationConnection
from boto.ec2 import EC2Connection

ec2_conn = EC2Connection()
cf_conn=CloudFormationConnection()
s3_conn = S3Connection()

iid = get_instance_metadata()['instance-id']
reservations = ec2_conn.get_all_instances(filters={'instance-id': '%s' %iid})
instance = reservations[0].instances[0]
tags= instance.tags

config_bucket_obj=cf_conn.describe_stack_resource(tags['aws:cloudformation:stack-name'],'s3globalconfig')
config_bucket=config_bucket_obj['DescribeStackResourceResponse']['DescribeStackResourceResult']['StackResourceDetail']['PhysicalResourceId']
name = tags['layer'] + '-' + tags['environment'] + '-' + iid

# Sumo Configuration
cb_obj = s3_conn.get_bucket(config_bucket, validate=False)
sumoconfk = cb_obj.new_key('/global/sumo.conf')
sumoconf = sumoconfk.get_contents_as_string()
sumoconf=sumoconf.replace("name=name", "name=%s" %name)
print sumoconf
if os.path.exists("/etc/sumo.conf"):
    os.remove("/etc/sumo.conf")
file = open("/etc/sumo.conf", "a")
file.write(sumoconf)
file.close()

# Sources file
sourceconfig = {}
sourceconfig["api.version"] = "v1"
sourceconfig["sources"] = []
    # Skynet Source
sourceconfig["sources"].append({})
sourceconfig["sources"][0]["sourceType"] = "LocalFile"
sourceconfig["sources"][0]["name"] = "Skynet Logs"
sourceconfig["sources"][0]["pathExpression"] = "/var/logs/skynet/supervisord.log"
sourceconfig["sources"][0]["category"] = "skynet"
    # Cloudformation Source
sourceconfig["sources"].append({})
sourceconfig["sources"][1]["sourceType"] = "LocalFile"
sourceconfig["sources"][1]["name"] = "CloudFormation Logs"
sourceconfig["sources"][1]["pathExpression"] = "/var/log/cfn-init.log"
sourceconfig["sources"][1]["category"] = "deployment"
    # Cloudformation Command Source
sourceconfig["sources"].append({})
sourceconfig["sources"][2]["sourceType"] = "LocalFile"
sourceconfig["sources"][2]["name"] = "CloudFormation Command Logs"
sourceconfig["sources"][2]["pathExpression"] = "/var/log/cfn-init-cmd.log"
sourceconfig["sources"][2]["category"] = "deployment"
    # Cloudformation Command Source
sourceconfig["sources"].append({})
sourceconfig["sources"][3]["sourceType"] = "LocalFile"
sourceconfig["sources"][3]["name"] = "Nginx Logs"
sourceconfig["sources"][3]["pathExpression"] = "/var/log/nginx/error.log"
sourceconfig["sources"][3]["category"] = "web-server"
print sourceconfig
if os.path.exists("/etc/config/default.sumo"):
    os.remove("/etc/config/default.sumo")
file = open("/etc/config/default.sumo", "a")
file.write(json.dumps(sourceconfig))
file.close()
subprocess.call("/etc/init.d/collector start", shell=True)