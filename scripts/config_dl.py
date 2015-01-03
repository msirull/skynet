import boto.iam, ast, boto.cloudformation, boto.ec2
from boto.utils import get_instance_metadata

region = get_instance_metadata()['placement']['availability-zone'][:-1]
iam_conn=boto.iam.connect_to_region('us-west-2')
cf_conn=boto.cloudformation.connect_to_region(region)
ec2_conn = boto.ec2.connect_to_region(region)

iid = get_instance_metadata()['instance-id']
reservations = ec2_conn.get_all_reservations(instance_ids='%s' %iid)
instance = reservations[0].instances[0]
tags= instance.tags

dynamo_config=cf_conn.describe_stack_resource(tags['aws:cloudformation:stack-name'],'configTable1')
tbl=dynamo_config['DescribeStackResourceResponse']['DescribeStackResourceResult']['StackResourceDetail']['PhysicalResourceId']
iam = get_instance_metadata()['iam']['security-credentials'].keys()[0]


dynamo_config="dynamodb-config"
dbpolicy=iam_conn.get_role_policy(iam,dynamo_config)
doc = dbpolicy['get_role_policy_response']['get_role_policy_result']['policy_document']
doc = doc.replace('%7B', '{')
doc = doc.replace('%22', '''"''')
doc = doc.replace('%3A', ':')
doc = doc.replace('%5B', '[')
doc = doc.replace('%5D', ']')
doc = doc.replace('%7D', '}')
doc = doc.replace('%2C', ',')
doc = doc.replace('%2F', '/')

ddoc = ast.literal_eval(doc)
ddoc = ddoc['Statement'][0]['Resource']