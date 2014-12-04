cd /etc/skynet/skynet-master
mkdir /var/log/skynet
find /etc/config -name "*.sh" -type f -exec chmod 775 {} \;
find /etc/skynet -name "*.sh" -type f -exec chmod 775 {} \;
./scripts/config_dl.sh /etc/config
cp ./generic_config/nginx.conf /etc/nginx/nginx.conf
cp ./generic_config/sshconfig /root/.ssh/config
./scripts/gitclone.sh
python ./scripts/service_registration.py
cp ./generic_config/supervisord.conf /etc/
cp ./generic_config/supervisord /etc/rc.d/init.d
chmod +x /etc/rc.d/init.d/supervisord
cp ./generic_config/skynet.supervisor /etc/config
cp ./scripts/skynet.py /etc/config/skynet_main.py