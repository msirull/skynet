pwd=`pwd`
mkdir /etc/config
find /etc/config -name "*.sh" -type f -exec chmod 775 {} \
find /etc/skynet -name "*.sh" -type f -exec chmod 775 {} \
$pwd/scripts/config_dl.sh /etc/config
cp $pwd/generic_config/nginx.conf /etc/nginx/nginx.conf
cp $pwd/generic_config/sshconfig /root/.ssh/config
$pwd/scripts/gitclone.sh
python $pwd/scripts/service_registration.py
cp $pwd/generic_config/supervisord.conf /etc/
cp $pwd/scripts/skynet.py /etc/config/skynet_main.py