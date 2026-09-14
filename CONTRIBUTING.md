# Contributing to BluePanel

BluePanel development happens in this repository:

```text
https://github.com/hazhanhasani/panel
```

## Development setup

```bash
git clone https://github.com/hazhanhasani/panel.git
cd panel
make setup-test
make install-front
```

Run the backend:

```bash
make run
```

Run the CLI:

```bash
make run-cli
```

Run tests and checks:

```bash
make test
make check
```

Build the dashboard:

```bash
./build_dashboard.sh
```

## BluePanel update policy

BluePanel installation and update paths must point to repositories owned by `hazhanhasani`. Do not add installer, release-check, Docker-image, advertisement, donation, or documentation dependencies that silently switch deployments back to an upstream project.

## Compatibility dependencies

Some package/import identifiers can temporarily retain their upstream technical namespace where changing them would require publishing a compatible replacement package. These are implementation dependencies, not BluePanel product branding. They should be migrated only together with their dependent packages to avoid breaking production builds.

## License

Keep the repository license and any legally required upstream notices intact when modifying or redistributing the project.
