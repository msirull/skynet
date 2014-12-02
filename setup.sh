mkdir /etc/config
./scripts/config_dl.sh /etc/config
cp ./generic_config/nginx.conf /etc/nginx/nginx.conf
cp ./generic_config/sshconfig /root/.ssh/config
./scripts/gitclone.sh
python ./dynamo_config.py
cp ./generic_config/supervisord.conf /etc/
cp ./scripts/skynet.py /etc/config/skynet_main.py