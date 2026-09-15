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
bluepanel version
```

BluePanel is installed under `/opt/bluepanel` and persistent data is stored under `/var/lib/bluepanel`.

The dashboard listens on port `8000` by default:

```text
http://SERVER_IP:8000/dashboard/
```

Create the one-time initial owner setup key:

```bash
bluepanel generate-temp-key
# Or pass any internal CLI command through the manager:
bluepanel cli generate-temp-key
```

## Enable SSL after installation

Point the domain's A/AAAA record at the server and allow inbound TCP port 80. After the HTTP panel is healthy, run:

```bash
bluepanel ssl panel.example.com admin@example.com
```

The command obtains a Let's Encrypt certificate with acme.sh, configures automatic renewal, writes the certificate paths to `/opt/bluepanel/.env`, and restarts the panel with HTTPS. Certificates persist under `/var/lib/bluepanel/certs`.

## Updates

`bluepanel update` fetches source only from:

```text
https://github.com/hazhanhasani/panel
```

It resets the local source tree to the latest official `main` commit, rebuilds the local BluePanel Docker image, applies database migrations, and restarts the service. SQLite and image rollback copies are made before updating. Use `bluepanel version` to display the installed version and commit.

The dashboard update checker also reads releases from this repository. Node release checks use `hazhanhasani/node`.

## BluePanel Node

The companion node repository is:

```text
https://github.com/hazhanhasani/node
```

Future Tor multi-exit functionality will be implemented between the BluePanel panel and BluePanel-compatible node layer.

## License and upstream attribution

BluePanel is a fork-derived project and retains the original open-source license and notices required by the repository license. Product branding, release feeds, installer paths and update sources are maintained independently by BluePanel.

