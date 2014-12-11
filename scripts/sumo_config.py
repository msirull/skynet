import json, os, subprocess
from boto.s3.connection import S3Connection
from boto.utils import get_instance_metadata
from boto.cloudformation import CloudFormationConnection
iid = get_instance_metadata()['instance-id']
cf_conn=CloudFormationConnection()
tags = file.read(open("/etc/config/tags.info", "r"))
ptags = json.loads(tags)

config_bucket_obj=cf_conn.describe_stack_resource(ptags['aws:cloudformation:stack-name'],'s3globalconfig') 
config_bucket=config_bucket_obj['DescribeStackResourceResponse']['DescribeStackResourceResult']['StackResourceDetail']['PhysicalResourceId']
name = ptags['layer'] + ptags['environment'] + iid

# Sumo Configuration
s3_conn = S3Connection()
cb_obj = s3_conn.get_bucket(config_bucket)
sumoconfk = cb_obj.new_key('sumo.conf')
sumoconf = sumoconfk.get_contents_as_string()
sumoconf.replace("name=name", "name="+name)
if os.path.exists("/etc/config/sumo.conf"):
    os.remove("/etc/config/sumo.conf")
file = open("/etc/config/sumo.conf", "a")
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
print sourceconfig
if os.path.exists("/etc/config/default.sumo"):
    os.remove("/etc/config/default.sumo")
file = open("/etc/config/default.sumo", "a")
file.write(json.dumps(sourceconfig))
file.close()
subprocess.call("/etc/init.d/collector start", shell=True)