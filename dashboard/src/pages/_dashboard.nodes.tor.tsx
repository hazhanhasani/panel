import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import http from '@/service/http'

interface TorLocation {
  id: number
  node_id: number
  slug: string
  display_name: string
  country_code: string
  base_inbound_tag: string
  enabled: boolean
  subscription_enabled: boolean
  sort_order: number
  desired_state: string
  sync_status: string
  health_status: string | null
  detected_country: string | null
  exit_ip: string | null
  latency_ms: number | null
  last_error: string | null
  xray_inbound_port: number | null
  tor_socks_port: number | null
  tor_control_port: number | null
}

interface TorSummary {
  total: number
  enabled: number
  healthy: number
  degraded: number
  pending: number
  errors: number
}

const EMPTY_FORM = {
  node_id: '',
  slug: '',
  display_name: '',
  country_code: '',
  base_inbound_tag: '',
  enabled: true,
  subscription_enabled: true,
  sort_order: 0,
}

export default function TorLocationsPage() {
  const [locations, setLocations] = useState<TorLocation[]>([])
  const [summary, setSummary] = useState<TorSummary | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [locationResponse, summaryResponse] = await Promise.all([
        http.get('/api/tor/locations'),
        http.get('/api/tor/summary'),
      ])
      setLocations(locationResponse.data)
      setSummary(summaryResponse.data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load Tor locations')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const statusCounts = useMemo(() => summary ?? {
    total: locations.length,
    enabled: locations.filter((location) => location.enabled).length,
    healthy: locations.filter((location) => location.health_status === 'healthy').length,
    degraded: locations.filter((location) => location.health_status === 'degraded').length,
    pending: locations.filter((location) => location.sync_status === 'pending').length,
    errors: locations.filter((location) => location.sync_status === 'error').length,
  }, [locations, summary])

  const createLocation = async () => {
    setSaving(true)
    setError(null)
    try {
      await http.post('/api/tor/locations', {
        ...form,
        node_id: Number(form.node_id),
        country_code: form.country_code.trim().toUpperCase(),
        slug: form.slug.trim().toLowerCase(),
        sort_order: Number(form.sort_order),
      })
      setForm(EMPTY_FORM)
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to create location')
    } finally {
      setSaving(false)
    }
  }

  const action = async (location: TorLocation, name: string) => {
    setError(null)
    try {
      await http.post(`/api/tor/locations/${location.id}/${name}`)
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || `Failed to ${name} location`)
    }
  }

  const remove = async (location: TorLocation) => {
    setError(null)
    try {
      await http.delete(`/api/tor/locations/${location.id}`)
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to delete location')
    }
  }

  const reconcile = async () => {
    setError(null)
    try {
      await http.post('/api/tor/reconcile')
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to reconcile locations')
    }
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tor Locations</h1>
          <p className="text-sm text-muted-foreground">Multi-country Tor exits managed by BluePanel Node with shared user identity and quota.</p>
        </div>
        <Button variant="outline" onClick={reconcile}>Reconcile all</Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        {[
          ['Total', statusCounts.total],
          ['Enabled', statusCounts.enabled],
          ['Healthy', statusCounts.healthy],
          ['Degraded', statusCounts.degraded],
          ['Pending', statusCounts.pending],
          ['Errors', statusCounts.errors],
        ].map(([label, value]) => (
          <Card key={String(label)}>
            <CardHeader className="pb-2"><CardDescription>{label}</CardDescription></CardHeader>
            <CardContent className="text-2xl font-semibold">{value}</CardContent>
          </Card>
        ))}
      </div>

      {error && <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</div>}

      <Card>
        <CardHeader>
          <CardTitle>Add location</CardTitle>
          <CardDescription>Ports are automatically allocated by the Node unless you manage them through advanced API fields.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="space-y-2"><Label>Node ID</Label><Input value={form.node_id} onChange={(event) => setForm({ ...form, node_id: event.target.value })} inputMode="numeric" /></div>
          <div className="space-y-2"><Label>Slug</Label><Input value={form.slug} onChange={(event) => setForm({ ...form, slug: event.target.value })} placeholder="de-berlin" /></div>
          <div className="space-y-2"><Label>Display name</Label><Input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} placeholder="Germany" /></div>
          <div className="space-y-2"><Label>Country code</Label><Input value={form.country_code} maxLength={2} onChange={(event) => setForm({ ...form, country_code: event.target.value })} placeholder="DE" /></div>
          <div className="space-y-2"><Label>Base inbound tag</Label><Input value={form.base_inbound_tag} onChange={(event) => setForm({ ...form, base_inbound_tag: event.target.value })} /></div>
          <div className="space-y-2"><Label>Sort order</Label><Input value={String(form.sort_order)} onChange={(event) => setForm({ ...form, sort_order: Number(event.target.value) })} inputMode="numeric" /></div>
          <div className="flex items-center gap-3"><Switch checked={form.enabled} onCheckedChange={(checked) => setForm({ ...form, enabled: checked })} /><Label>Enabled</Label></div>
          <div className="flex items-center gap-3"><Switch checked={form.subscription_enabled} onCheckedChange={(checked) => setForm({ ...form, subscription_enabled: checked })} /><Label>Visible in subscriptions</Label></div>
          <div className="md:col-span-2 xl:col-span-3"><Button onClick={createLocation} disabled={saving || !form.node_id || !form.slug || form.country_code.length !== 2 || !form.base_inbound_tag}>{saving ? 'Creating…' : 'Create location'}</Button></div>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {loading ? <Card><CardContent className="p-6 text-sm text-muted-foreground">Loading…</CardContent></Card> : locations.map((location) => (
          <Card key={location.id}>
            <CardHeader className="gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <CardTitle className="flex flex-wrap items-center gap-2">
                  {location.display_name || location.slug}
                  <Badge variant={location.health_status === 'healthy' ? 'default' : 'secondary'}>{location.health_status || 'unknown'}</Badge>
                  <Badge variant="outline">{location.sync_status}</Badge>
                </CardTitle>
                <CardDescription>{location.country_code} · Node {location.node_id} · {location.base_inbound_tag}</CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => action(location, location.enabled ? 'disable' : 'enable')}>{location.enabled ? 'Disable' : 'Enable'}</Button>
                <Button size="sm" variant="outline" onClick={() => action(location, 'restart')}>Restart</Button>
                <Button size="sm" variant="outline" onClick={() => action(location, 'new-identity')}>New IP</Button>
                <Button size="sm" variant="outline" onClick={() => action(location, 'repair')}>Repair</Button>
                <Button size="sm" variant="outline" onClick={() => action(location, 'test')}>Test</Button>
                <Button size="sm" variant="destructive" onClick={() => remove(location)}>Delete</Button>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div><span className="text-muted-foreground">Exit IP:</span> {location.exit_ip || '—'}</div>
              <div><span className="text-muted-foreground">Detected:</span> {location.detected_country || '—'}</div>
              <div><span className="text-muted-foreground">Latency:</span> {location.latency_ms == null ? '—' : `${location.latency_ms} ms`}</div>
              <div><span className="text-muted-foreground">Inbound port:</span> {location.xray_inbound_port || 'auto'}</div>
              {location.last_error && <div className="sm:col-span-2 lg:col-span-4 rounded-md bg-muted p-3 text-destructive">{location.last_error}</div>}
            </CardContent>
          </Card>
        ))}
        {!loading && locations.length === 0 && <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">No Tor locations configured.</CardContent></Card>}
      </div>
    </div>
  )
}
