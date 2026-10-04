/** Fleet map builder — mirrors Nuxt `useFleetMap` (Leaflet topo/hillshade). */
export interface FleetLocation {
	unit: string;
	unit_type?: string;
	status?: string;
	color_hex: string;
	level?: string;
	lat: number;
	lng: number;
	health?: number;
	fuel?: string;
	operator?: string;
	speed?: string;
	temp?: string;
	last_update?: string;
}

/** Escape untrusted values before interpolating into marker/popup HTML. */
function esc(v: unknown): string {
	return String(v ?? '')
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#39;');
}

/** Only allow a safe colour token (hex / rgb) to reach inline styles. */
function safeColor(v?: string): string {
	return typeof v === 'string' && /^#[0-9a-fA-F]{3,8}$/.test(v.trim()) ? v.trim() : '#7A848E';
}

function buildMarkerHtml(loc: FleetLocation): string {
	const color = safeColor(loc.color_hex);
	return `
    <span class="fleet-pulse" style="background:${color}"></span>
    <span class="fleet-dot" style="background:${color}"><b>${esc(loc.level || '•')}</b></span>
    <span class="fleet-label">${esc(loc.unit)}</span>`;
}

function row(label: string, val?: string | number): string {
	return val === undefined || val === null || val === ''
		? ''
		: `<tr><td style="padding-bottom:5px;color:#5d6b7a;">${esc(label)}</td><td style="font-weight:700;text-align:right;">${esc(val)}</td></tr>`;
}

function buildPopupHtml(loc: FleetLocation): string {
	return `
    <div style="font-family:'Inter',sans-serif;min-width:220px;border-radius:12px;overflow:hidden;">
      <div style="background-color:${safeColor(loc.color_hex)};color:#fff;padding:12px;">
        <h4 style="font-weight:800;font-size:17px;margin:0;">${esc(loc.unit)}</h4>
        <p style="margin:0;font-size:12px;opacity:.9;">${esc(loc.unit_type || 'Heavy Equipment')}</p>
      </div>
      <div style="padding:12px;background-color:#fff;">
        <table style="width:100%;font-size:12px;border-collapse:collapse;color:#1b2128;">
          ${row('Status', loc.status)}
          ${row('Health', loc.health !== undefined ? loc.health + '%' : undefined)}
          ${row('Operator', loc.operator)}
          ${row('Speed', loc.speed)}
          ${row('Suhu Mesin', loc.temp)}
          ${row('Fuel Level', loc.fuel)}
        </table>
        <div style="margin-top:10px;padding-top:8px;border-top:1px dashed #d7dde4;font-size:10px;text-align:center;color:#5d6b7a;font-family:'JetBrains Mono',monospace;">
          ${loc.lat.toFixed(4)}, ${loc.lng.toFixed(4)}${loc.last_update ? ' · <b>' + esc(loc.last_update) + '</b>' : ''}
        </div>
      </div>
    </div>`;
}

export async function createMap(
	containerId: string,
	locations: FleetLocation[],
	opts: { zoom?: number; dark?: boolean } = {}
): Promise<any> {
	if (typeof window === 'undefined') return null;
	const el = document.getElementById(containerId);
	if (!el) return null;

	const L = (await import('leaflet')).default;

	const map = L.map(containerId, {
		center: [-0.5032, 117.1536],
		zoom: opts.zoom ?? 13,
		minZoom: 4,
		maxZoom: 18,
		zoomControl: false,
		attributionControl: false
	});
	L.control.zoom({ position: 'topright' }).addTo(map);
	L.control.attribution({ position: 'bottomright', prefix: false }).addTo(map);

	L.tileLayer(
		'https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}',
		{ maxZoom: 18, maxNativeZoom: 16, attribution: 'Hillshade © Esri' }
	).addTo(map);
	L.tileLayer(
		'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
		{ maxZoom: 18, maxNativeZoom: 18, opacity: 0.82, attribution: 'Tiles © Esri — World Topo Map' }
	).addTo(map);

	el.classList.toggle('map-dark', !!opts.dark);

	const markers: any[] = [];
	locations.forEach((loc) => {
		if (typeof loc.lat !== 'number' || typeof loc.lng !== 'number') return;
		const icon = L.divIcon({
			className: 'fleet-marker',
			html: buildMarkerHtml(loc),
			iconSize: [54, 54],
			iconAnchor: [27, 44],
			popupAnchor: [0, -42]
		});
		const m = L.marker([loc.lat, loc.lng], { icon })
			.addTo(map)
			.bindPopup(buildPopupHtml(loc), { closeButton: false, className: 'modern-popup' });
		markers.push(m);
	});

	if (markers.length > 1) {
		const grp = L.featureGroup(markers);
		map.fitBounds(grp.getBounds().pad(0.25), { maxZoom: 15 });
	} else if (markers.length === 1) {
		map.setView([locations[0].lat, locations[0].lng], 14);
	}

	setTimeout(() => map.invalidateSize(), 200);
	return map;
}
