from boto.dynamodb2.table import Table
import json, os, subprocess
from boto.utils import get_instance_metadata
from boto.ec2 import EC2Connection

ec2_conn = EC2Connection()

iid = get_instance_metadata()['instance-id']
reservations = ec2_conn.get_all_instances(filters={'instance-id': '%s' %iid})
instance = reservations[0].instances[0]
tags= instance.tags


# Register with DynamoDB
env = tags['environment']
tbl = "endpoints"
locations = {}
table_obj = Table(tbl)
table_obj.put_item(data={
	'env': tags['environment'],
	'layer': tags['layer'],
	'url': tags['elb_url']
}, overwrite=True)
