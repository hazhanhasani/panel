# BluePanel Dashboard

Web dashboard for BluePanel.

## Development

```bash
git clone https://github.com/hazhanhasani/panel.git
cd panel/dashboard
curl -fsSL https://bun.sh/install | bash
bun install
bun dev
```

Set the backend API base URL when needed:

```env
VITE_BASE_API=https://example.com/
```

Production build:

```bash
bun build
```

The BluePanel product repository is `https://github.com/hazhanhasani/panel`.
