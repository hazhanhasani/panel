# BluePanel

BluePanel is a self-hosted proxy management panel for Xray-based services, user management, subscriptions, multi-node deployments, traffic limits, statistics and automation.

This repository is the canonical source for the BluePanel build, installer and updates.

## Quick install

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/hazhanhasani/panel/main/install.sh)" @ install
```

After installation:

```bash
bluepanel status
bluepanel logs
bluepanel update
bluepanel restart
```

BluePanel is installed under `/opt/bluepanel` and persistent data is stored under `/var/lib/bluepanel`.

The dashboard listens on port `8000` by default:

```text
http://SERVER_IP:8000/dashboard/
```

Create the initial owner setup key:

```bash
cd /opt/bluepanel
docker compose -p bluepanel exec bluepanel bluepanel-cli generate-temp-key
```

## Updates

`bluepanel update` fetches source only from:

```text
https://github.com/hazhanhasani/panel
```

It resets the local source tree to the current `main` branch, rebuilds the local BluePanel Docker image and restarts the BluePanel service. It does not use the upstream installer or upstream Docker image.

The dashboard update checker also reads releases from this repository. Node release checks use `hazhanhasani/node`.

## BluePanel Node

The companion node repository is:

```text
https://github.com/hazhanhasani/node
```

Future Tor multi-exit functionality will be implemented between the BluePanel panel and BluePanel-compatible node layer.

## License and upstream attribution

BluePanel is a fork-derived project and retains the original open-source license and notices required by the repository license. Product branding, release feeds, installer paths and update sources are maintained independently by BluePanel.
