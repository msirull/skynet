import json

sourceconfig = {}
sourceconfig["api.version"] = "v1"
sourceconfig["sources"] = []
sourceconfig["sources"].append({})
sourceconfig["sources"][0]["sourceType"] = "LocalFile"
sourceconfig["sources"][0]["name"] = "Skynet Logs"
sourceconfig["sources"][0]["pathExpression"] = "/var/logs/skynet/supervisord.log"
sourceconfig["sources"][0]["category"] = "skynet"
sourceconfig["sources"].append({})
sourceconfig["sources"][1]["sourceType"] = "LocalFile"
sourceconfig["sources"][1]["name"] = "CloudFormation Logs"
sourceconfig["sources"][1]["pathExpression"] = "/var/log/cfn-init.log"
sourceconfig["sources"][1]["category"] = "deployment"
print sourceconfig