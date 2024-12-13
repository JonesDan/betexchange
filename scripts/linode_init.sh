# update dynu DNS
cd ~
mkdir /opt/dynudns
echo "echo url=\"https://${dynu_user}:${dynu_pwd}@api.dynu.com/nic/update?hostname=${dynu_hostname}&myip=${linode_ip}&myipv6=no\" | curl -k -o /opt/dynudns/dynu.log -K -" > /opt/dynudns/dynu.sh
chmod 700 /opt/dynudns/dynu.sh
bash /opt/dynudns/dynu.sh
(crontab -l 2>/dev/null; echo "*/5 * * * *  /opt/dynudns/dynu.sh -with args") | crontab -

sudo apt -y remove needrestart

# install docker compose
sudo apt update
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker

# start containers
cd /opt/app
docker-compose up -d
