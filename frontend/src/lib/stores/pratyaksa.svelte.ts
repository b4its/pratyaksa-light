/**
 * Pratyaksa store — fleet polling for the simulation-only backend.
 *
 * The backend always runs in SIMULATION mode; every fleet/health/result payload
 * comes from the internal deterministic simulator. There is no live/external
 * ML API, so this store no longer tracks mode switching or ML target URLs.
 */
import { env } from '$env/dynamic/public';

const baseURL = env.PUBLIC_API_BASE || 'http://localhost:8116/api/v1';

/** GET + parse JSON, throwing a readable error on HTTP/parse failure. */
async function getJson(path: string): Promise<any> {
	const res = await fetch(`${baseURL}${path}`);
	const text = await res.text();
	let data: any = null;
	if (text) {
		try {
			data = JSON.parse(text);
		} catch {
			data = null;
		}
	}
	if (!res.ok) {
		throw new Error(data?.message || data?.detail || `HTTP ${res.status}`);
	}
	return data;
}

export interface FleetAsset {
	asset_id: string;
	equipment_type: string;
	risk_level: string;
	lstm_rul_hours: number;
	rul_uncertainty: number;
	model_agreement: boolean;
	drift_detected: boolean;
	processed_at: number;
}

class PratyaksaStore {
	status = $state<{
		mode: 'simulasi';
		fleet_count: number;
	}>({ mode: 'simulasi', fleet_count: 0 });

	fleetData = $state<FleetAsset[]>([]);
	fleetHealth = $state({ total: 0, normal: 0, warning: 0, critical: 0, avg_rul_hours: 0 });
	isLoading = $state(false);
	error = $state<string | null>(null);

	private timer: ReturnType<typeof setInterval> | null = null;

	async fetchStatus() {
		try {
			const res = await getJson('/pratyaksa/status');
			this.status = res.data;
			this.error = null;
			return res.data;
		} catch (e: any) {
			this.error = e?.message || 'Gagal fetch status';
			return null;
		}
	}

	async fetchFleet() {
		try {
			const res = await getJson('/pratyaksa/fleet');
			this.fleetData = res.data.fleet;
			this.error = null;
			return res.data;
		} catch (e: any) {
			this.error = e?.message || 'Gagal fetch fleet';
			return null;
		}
	}

	async fetchFleetHealth() {
		try {
			const res = await getJson('/pratyaksa/fleet/health');
			this.fleetHealth = res.data;
			this.error = null;
			return res.data;
		} catch (e: any) {
			this.error = e?.message || 'Gagal fetch fleet health';
			return null;
		}
	}

	async fetchResult(assetId: string) {
		try {
			const res = await getJson(`/pratyaksa/result/${assetId}`);
			return res.data;
		} catch {
			return null;
		}
	}

	async fetchExplain(predictionId: string) {
		try {
			const res = await getJson(`/pratyaksa/explain/${predictionId}`);
			return res.data;
		} catch {
			return null;
		}
	}

	async fetchAll() {
		this.isLoading = true;
		this.error = null;
		await Promise.all([this.fetchStatus(), this.fetchFleet(), this.fetchFleetHealth()]);
		this.isLoading = false;
	}

	startPolling(intervalMs = 5000) {
		this.stopPolling();
		this.timer = setInterval(() => this.fetchAll(), intervalMs);
	}

	stopPolling() {
		if (this.timer) {
			clearInterval(this.timer);
			this.timer = null;
		}
	}
}

export const pratyaksa = new PratyaksaStore();
