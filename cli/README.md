# BluePanel CLI

The BluePanel command-line interface is included in the BluePanel image and source tree.

## Commands

```bash
bluepanel-cli --help
bluepanel-cli version
bluepanel-cli generate-temp-key
```

From the project source tree:

```bash
uv run bluepanel-cli.py --help
```

For an installed Docker deployment:

```bash
cd /opt/bluepanel
docker compose -p bluepanel exec bluepanel bluepanel-cli generate-temp-key
```
