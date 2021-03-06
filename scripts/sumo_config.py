import json, os, subprocess
from boto.utils import get_instance_metadata
import boto.cloudformation, boto.ec2, boto.s3

region = get_instance_metadata()['placement']['availability-zone'][:-1]

ec2_conn = boto.ec2.connect_to_region(region)
cf_conn=boto.cloudformation.connect_to_region(region)
s3_conn = boto.s3.connect_to_region(region)

iid = get_instance_metadata()['instance-id']
reservations = ec2_conn.get_all_reservations(instance_ids='%s' %iid)
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
sourceconfig["sources"][0]["pathExpression"] = "/var/logs/skynet/*.log"
sourceconfig["sources"][0]["category"] = "skynet"
sourceconfig["sources"][0]["timeZone"] = "UTC"
    # Cloudformation Source
sourceconfig["sources"].append({})
sourceconfig["sources"][1]["sourceType"] = "LocalFile"
sourceconfig["sources"][1]["name"] = "CloudFormation Logs"
sourceconfig["sources"][1]["pathExpression"] = "/var/log/cfn-init.log"
sourceconfig["sources"][1]["category"] = "deployment"
sourceconfig["sources"][1]["timeZone"] = "UTC"
    # Cloudformation Command Source
sourceconfig["sources"].append({})
sourceconfig["sources"][2]["sourceType"] = "LocalFile"
sourceconfig["sources"][2]["name"] = "CloudFormation Command Logs"
sourceconfig["sources"][2]["pathExpression"] = "/var/log/cfn-init-cmd.log"
sourceconfig["sources"][2]["category"] = "deployment"
sourceconfig["sources"][2]["timeZone"] = "UTC"
    # Nginx Source
sourceconfig["sources"].append({})
sourceconfig["sources"][3]["sourceType"] = "LocalFile"
sourceconfig["sources"][3]["name"] = "Nginx Logs"
sourceconfig["sources"][3]["pathExpression"] = "/var/log/nginx/error.log"
sourceconfig["sources"][3]["category"] = "web-server"
sourceconfig["sources"][3]["timeZone"] = "UTC"

if os.path.exists("/etc/config/default.sumo"):
    os.remove("/etc/config/default.sumo")
file = open("/etc/config/default.sumo", "a")
file.write(json.dumps(sourceconfig))
file.close()
subprocess.call("/etc/init.d/collector restart", shell=True)