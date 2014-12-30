from boto.dynamodb2.table import Table
import json, os, subprocess
from boto.utils import get_instance_metadata
import boto.ec2
region = get_instance_metadata()['placement']['availability-zone'][:-1]
ec2_conn = boto.ec2.connect_to_region(region)

iid = get_instance_metadata()['instance-id']
reservations = ec2_conn.get_all_instances(filters={'instance-id': '%s' %iid})
instance = reservations[0].instances[0]
tags= instance.tags


# Register with DynamoDB
def main():
	tbl = "endpoints"
	table_obj = Table(tbl)
	table_obj.put_item(data={
		'env': tags['environment'],
		'layer': tags['layer'],
		'url': tags['elb_url']
	}, overwrite=True)

if __name__ == '__main__':
	main()