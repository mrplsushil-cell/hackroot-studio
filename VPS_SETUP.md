# VPS_SETUP — Hackroot Studio v1.0

Step-by-step host provisioning on a fresh **Ubuntu 24.04 LTS** VPS, before
deploying the application.

## 1. Initial access & user
```bash
ssh root@<server-ip>
adduser deploy
usermod -aG sudo deploy
# (optional) copy your SSH key: ssh-copy-id deploy@<server-ip>
```
Disable root SSH login and password auth in `/etc/ssh/sshd_config`
(`PermitRootLogin no`, `PasswordAuthentication no`), then `systemctl restart ssh`.

## 2. System update
```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install ca-certificates curl gnupg lsb-release git gzip tar ufw
sudo reboot   # if kernel updated
```

## 3. Install Docker Engine
```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker deploy
newgrp docker   # or re-login so 'deploy' can run docker without sudo
docker version && docker compose version
```

## 4. Firewall (ufw)
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```
> Only 22 (SSH), 80, and 443 are exposed. Postgres (5432) and Redis are internal
> to the Docker network and are NOT published.

## 5. Project files
```bash
cd /opt
sudo mkdir -p hackroot && sudo chown deploy:deploy hackroot
git clone <your-repo> hackroot   # or scp the project tree
cd hackroot
cp production.env.example production.env
chmod 600 production.env         # secrets file — never commit
```

## 6. Storage disk (optional, larger volume)
If you attached a block device for media:
```bash
sudo mkfs.ext4 /dev/sdb
sudo mkdir -p /var/lib/docker/volumes/hackrootai_storage_data/_data
sudo mount /dev/sdb /var/lib/docker/volumes/hackrootai_storage_data/_data
# add to /etc/fstab for persistence
```
(Adjust the volume name — Compose prefixes it with the project dir name, e.g.
`hackrootai_storage_data`.)

## 7. (Optional) log rotation outside Docker
The compose file already uses the Docker `json-file` driver
(`max-size=50m`, `max-file=5`). If you also want host-level rotation of any
files you write (e.g. certbot logs), a standard `logrotate` config applies.

## 8. Verify
```bash
docker compose -f docker-compose.prod.yml config   # validates the compose file
```
Proceed to DOMAIN_SETUP.md → SSL_SETUP.md → deployment.
