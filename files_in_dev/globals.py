from boto.utils import get_instance_metadata
from boto.sqs.message import RawMessage
import boto.sqs, boto.ec2, json

def var():
    iid = get_instance_metadata()['instance-id']
    tags = file.read(open("/etc/config/tags.info", "r"))
    ptags = json.loads(tags)
    ec2_conn = boto.ec2.connect_to_region('us-west-2')
    sqs_conn = boto.sqs.connect_to_region("us-west-2")
    reservations = ec2_conn.get_all_instances(filters={"tag:maintenance-group" : ptags["maintenance-group"]})
    instances = [i for r in reservations for i in r.instances]
    ips = [i.ip_address for i in instances]
    q = sqs_conn.create_queue('test-prod-maint')
    m = RawMessage()
    msg_src = []
    msg_type = []
    #iid = ["i-9eba6394"]
    work_dir="/etc/app/"
    services = ["nginx", "php-fpm-5.5"]
    webroot="/var/www/html/"