/etc/config/config_dl.sh /etc/config
mv /etc/skynet/generic_config/nginx.conf /etc/nginx/nginx.conf
mv /etc/skynet/generic_config/sshconfig /root/.ssh/config
/etc/config/gitclone.sh
python /etc/config/dynamo_config.py
mv /etc/config/supervisord.conf /etc/
cp /etc/config/skynet.py /etc/config/skynet_main.py