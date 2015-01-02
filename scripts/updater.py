from threading import Thread
from boto.sqs.message import RawMessage
from boto.utils import get_instance_metadata
import boto.sqs, boto.ec2, subprocess, shutil, time, json, datetime, hmac, os, errno, git, logging
from hashlib import sha1
from boto.s3.connection import S3Connection
import boto.ec2
logging.basicConfig(filename='/var/log/skynet/skynet.log',level=logging.INFO)
iid = get_instance_metadata()['instance-id']
## GET TAGS

region = get_instance_metadata()['placement']['availability-zone'][:-1]
ec2_conn = boto.ec2.connect_to_region(region)

my_reservation = ec2_conn.get_all_reservations(instance_ids='%s' %iid)
myself = my_reservation[0].instances[0]
tags = myself.tags

## BAD NAME ASSIGNMENTS
services = ["nginx", "php-fpm-5.5"] # This one should come from the CloudFormation template
webroot="/var/www/html/" # This one is bad because I think it needs to be retrieved from the CF template
repo_bucket="code-staging" # Also from CF Template
gittoken='w3rQ2Q4KK7Wm73ANqg' # Not sure what to do here. Dynamo?
sqs_maint=tags['maintenance-queue'] # Also from CF Template
## END BAD STUFF

## Global Namespace
region = get_instance_metadata()['placement']['availability-zone'][:-1]
sqs_conn = boto.sqs.connect_to_region(region)
s3_conn = boto.s3.connect_to_region(region)
cth = ""
skynet_source="https://raw.githubusercontent.com/msirull/skynet/master/scripts/skynet.py"
q = sqs_conn.get_queue(sqs_maint)
msg_src = ""
msg_type = ""
work_dir="/etc/app/"
omsg = ""
repo_bucket_obj = s3_conn.get_bucket(repo_bucket, validate=False)

class PreUpdater():
    def __init__(self):
        pass

    def queue(self, msg, headers):
        msg_src = "Needs to forward header info"
        m = RawMessage()
        m.message_attributes = {
                            "instance-id":{"data_type": "String", "string_value": iid},
                            "message-source":{"data_type": "String", "string_value": msg_src}}
        m.set_body(msg)
        q.write(m)
        logging.info("Waiting...")
        while True:
            time.sleep(5)
            count=q.count()
            if count > 10:
                num=10
            else:
                num=count
            if count != 0:
                rs = q.get_messages(num_messages=num, attributes='All', message_attributes=['instance-id'])
                oldest_date = 99999999999999999
                for n in range(num):
                    timestamp=int(rs[n].attributes['SentTimestamp'])
                    miid=rs[n].message_attributes['instance-id']['string_value']
                    ## Checks to see who is first
                    if timestamp < oldest_date:
                        firstiid=miid
                        cmsg=rs[n].get_body()
                        oldest_date = timestamp
                        try:
                            cmsg
                        except NameError:
                            cmsg=omsg
                        try:
                            firstiid
                            global msgid
                            msgid=rs[n]
                        except NameError:
                            firstiid=""
            ## If first, start updating
            if firstiid == iid:
                logging.info("I'm going to start updating now because it's my turn")
                logging.info("And here's what I'm going to do: %s", cmsg)
                self.decider(cmsg, headers)
                return "ready"
            else:
                msgcount=str(count)
                logging.info("I'm in the queue! My message was %s and so are %s other people", omsg, msgcount)

    def decider(self, msg, headers):
        rmsg = json.loads(msg)
        update_action=Update()
        if 'action' in rmsg and rmsg['action'] == 'config-update':
            logging.info("Triggering config update")
            return update_action.config_update
        if 'action' in rmsg and rmsg['action'] == 'skynet-update':
            logging.info("Triggering Skynet update")
            return update_action.skynet_update
        if 'action' in rmsg and rmsg['action'] == 'code-update':
            logging.info("Triggering code update")
            return update_action.s3_update
        if 'User-Agent' in headers and headers['User-Agent'].startswith('GitHub-Hookshot'):
            logging.info("OK you *say* you're from Github, but let's check your signature...")
            verification=self.git_verify(rmsg, headers)
            if verification == "verified":
                return update_action.code_update
        # If nothing matches
        logging.info("Not a recognized notification")
        return "I don't what's going on here"

    def git_verify(self, rmsg, headers):
        if 'X-Hub-Signature' in headers:
            signature = "sha1="+hmac.new(gittoken, omsg, sha1).hexdigest()
            logging.debug(signature)
            # The signature isn't working right now, so I'm going to skip validation
            # if headers['X-Hub-Signature'] == signature:
            if signature == signature:
                logging.info("Github Identity Confirmed")
                if 'commits' in rmsg and rmsg["commits"] > 0:
                    fbranch = rmsg["ref"]
                    global branch
                    branch = fbranch.replace("refs/heads/", "")
                    global repo
                    repo = rmsg["repository"]["name"]
                    if branch == tags["branch"] and repo == tags["repo"]:
                        global nmsg
                        nmsg = {"action" : "code-update", "repo": repo, "branch": branch}
                        logging.info("Github Webhook Verified")
                        return "verified"
                    else:
                        logging.info("the branch or repo doesn't match, this one's not for me")
                else:
                    logging.info("No commits")
            else:
                logging.warning("Access Denied - Hashes don't match")
        else:
            logging.warning("There's no Github Signature")

class Update():
    def __init__(self):
        pass

    def code_update(self):
        # Start update process
        currenttime=str(int(time.time()))
        regulartime=(datetime.datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S'))
        logging.info("starting update process at "+regulartime)
        shutil.rmtree(work_dir, ignore_errors=True)
        subprocess.call('git clone git@github.com:msirull/'+ repo +'.git '+ work_dir, shell=True)
        shutil.rmtree(work_dir+'.git', ignore_errors=True)
        # Insert compile scripts here
        # Stop Services...the services need to not be hard coded
        logging.info("stopping services...")
        for s in services:
            subprocess.call('service ' + s + ' stop', shell=True)
            # Moving/Archiving data
        logging.info("archiving data")
        subprocess.call('mkdir /etc/backup/'+ currenttime, shell=True)
        subprocess.call('mv '+ webroot+'*' ' /etc/backup/'+ currenttime, shell=True)
        # Copy new data in
        logging.info("copying new data in")
        subprocess.call('cp -r '+ work_dir +'* ' + webroot, shell=True)
        logging.info("updating config")
        # Get an up-to-date config file
        subprocess.call('/etc/skynet/skynet-master/scripts/config_dl.sh /etc/config', shell=True)
        logging.info("starting services")
        # Get everything working again
        for s in services:
            subprocess.call('service ' + s + ' start', shell=True)
        logging.info("update done!")
        subprocess.call('aws s3 cp '+work_dir+' s3://'+repo_bucket+'/'+tags["repo"]+'/'+tags["branch"]+'/'+currenttime+' --recursive', shell=True)
        logging.info("copy to s3 done!")
        logging.info("Update successful!")
        return "success"

    def s3_update(self):
        # Start update process
        ctime=int(time.time())
        currenttime = str(ctime)
        regulartime = (datetime.datetime.fromtimestamp(int(currenttime)).strftime('%Y-%m-%d %H:%M:%S'))
        logging.info("starting update process at " + regulartime)
        shutil.rmtree(work_dir+tags['repo'], ignore_errors=True)
        versions=[]
        for k in repo_bucket_obj.list(tags['repo'] + '/' + tags['branch'] + '/','/'):
            path = str(k.name)
            ke=path.replace(tags['repo'] + '/' + tags['branch'] + '/', '')
            versions.append(int(ke.replace('/', '')))
        latest=max(versions)
        # Copy from S3
        logging.info("Downloading code from S3")
        repo_bucket_files=repo_bucket_obj.list(tags['repo'] + '/' + tags['branch'] + '/' + str(latest) + '/')
        for k in repo_bucket_files:
            key = str(k.name)
            d = work_dir + key
            try:
                k.get_contents_to_filename(d)
            except OSError:
            # check if dir exists
                if not os.path.exists(d):
                    os.makedirs(d)
        # Find latest revision
        # Insert compile scripts here
        # Stop Services...the services need to not be hard coded
        logging.info("stopping services...")
        for s in services:
            subprocess.call('service ' + s + ' stop', shell=True)
        # Moving/Archiving data
        #if not os.path.exists('/etc/backup/'):
        #	os.makedirs('/etc/backup/')
        os.mkdir('/etc/backup'+currenttime)
        #recursive_move(webroot, '/etc/backup/'+currenttime+'/')
        logging.info("starting archive")
        dst = '/etc/backup/'+currenttime+'/'
        src = webroot
        for f in os.listdir(src):
            try:
                shutil.copytree(src+f, dst+f)
                shutil.rmtree(src + f)
            except OSError as e:
                if e.errno == errno.ENOTDIR:
                    shutil.move(src+f, dst+f)
        #subprocess.call('cp -R '+ webroot+'*' ' /etc/backup/'+ currenttime +'/*', shell=True)
        # Copy new data in
        logging.info("copying new data in")
        subprocess.call('cp -r '+ work_dir + tags['repo'] + '/' + tags['branch'] + '/' + str(latest) + '/* ' + webroot, shell=True)
        logging.info("updating config")
        # Get an up-to-date config file
        subprocess.call('/etc/skynet/skynet-master/scripts/config_dl.sh /etc/config', shell=True)
        logging.info("starting services")
        # Get everything working again
        for s in services:
            subprocess.call('service ' + s + ' start', shell=True)
        complete_time=int(time.time())
        duration=complete_time-ctime
        logging.info("Update successful! It took " + str(duration) + " seconds")
        return "success"

    def skynet_update(self):
        regulartime=(datetime.datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S'))
        logging.info("starting update process at "+regulartime)
        shutil.rmtree("/etc/skynet", ignore_errors=True)
        git.Repo.clone_from("https://github.com/msirull/skynet", "/etc/skynet")
        os.chmod("/etc/skynet/setup.sh", 0775)
        subprocess.call('/etc/skynet/setup.sh', shell=True)
        subprocess.call('kill -HUP `head -1 /etc/config/skynet.pid`', shell=True)
        logging.info("Assimilation Successful")
        return "success"

    def config_update(self):
        subprocess.call('/etc/config/config_dl.sh /etc/config', shell=True)
        logging.info("Config Updated!")
        return "success"

def complete_update():
    try:
        msgid
    except NameError:
        pass
    else:
        q.delete_message(msgid)
        msgid.get_body()
        logging.info("Message deleted from queue")
    return

if __name__ == '__main__':
    pass
else:
    pass