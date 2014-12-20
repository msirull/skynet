#!/bin/sh
dir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
mkdir /var/log/skynet
find /etc/config -name "*.sh" -type f -exec chmod 775 {} \;
find /etc/skynet -name "*.sh" -type f -exec chmod 775 {} \;
$dir/scripts/config_dl.sh /etc/config
cp $dir/generic_config/nginx.conf /etc/nginx/
cp $dir/generic_config/sshconfig /root/.ssh/config
$dir/scripts/gitclone.sh
python $dir/scripts/service_registration.py
python $dir/scripts/sumo_config.py
cp $dir/generic_config/skynet-nginx.locations /etc/config/
cp $dir/generic_config/supervisord.conf /etc/
cp $dir/generic_config/supervisord /etc/rc.d/init.d
chmod +x /etc/rc.d/init.d/supervisord
cp $dir/generic_config/skynet.supervisor /etc/config
cp $dir/scripts/skynet.py /etc/config/skynet_main.py
kill -HUP `head -1 /etc/config/skynet.pid`