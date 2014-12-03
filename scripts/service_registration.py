from boto.dynamodb2.table import Table
import json, os, subprocess
from boto.utils import get_instance_metadata
tags = file.read(open("/etc/config/tags.info", "r"))
ptags = json.loads(tags)
env = ptags['environment']
tbl = "endpoints"
locations = {}
table_obj = Table(tbl)
table_obj.put_item(data={
	'env': ptags['environment'],
	'layer': ptags['layer'],
	'url': ptags['elb_url']
})
