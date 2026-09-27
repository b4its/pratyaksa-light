/** Pratyaksa store — mirrors Nuxt `usePratyaksa` (live/simulasi fleet polling). */
import { env } from '$env/dynamic/public';

const baseURL = env.PUBLIC_API_BASE || 'http://localhost:8080/api/v1';

export type BackendMode = 'live' | 'simulasi';
export type SourceMode = 'live-silent' | 'live-telegram' | 'hit-endpoint-sendiri' | 'hit-endpoint-ml';

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
		mode: BackendMode;
		manual_mode: string | null;
		api_reachable: boolean;
		fleet_count: number;
	}>({ mode: 'simulasi', manual_mode: null, api_reachable: false, fleet_count: 0 });

	fleetData = $state<FleetAsset[]>([]);
	fleetHealth = $state({ total: 0, normal: 0, warning: 0, critical: 0, avg_rul_hours: 0 });
	isLoading = $state(false);
	error = $state<string | null>(null);
	sourceMode = $state<SourceMode>('live-silent');

	mlTargetUrl = env.PUBLIC_ML_TARGET_URL || 'http://192.168.101.3:6000';
	customTargetUrl = env.PUBLIC_CUSTOM_TARGET_URL || 'http://192.168.101.3:7000';

	private timer: ReturnType<typeof setInterval> | null = null;

	get isLive() {
		return this.status.mode === 'live';
	}
	get isSimulasi() {
		return this.status.mode === 'simulasi';
	}

	async fetchStatus() {
		try {
			const res = await fetch(`${baseURL}/pratyaksa/status`).then((r) => r.json());
			this.status = res.data;
			return res.data;
		} catch (e: any) {
			this.error = e?.message || 'Gagal fetch status';
			return null;
		}
	}

	async fetchFleet() {
		try {
			const res = await fetch(`${baseURL}/pratyaksa/fleet`).then((r) => r.json());
			this.fleetData = res.data.fleet;
			this.status.mode = res.data.mode;
			return res.data;
		} catch (e: any) {
			this.error = e?.message || 'Gagal fetch fleet';
			return null;
		}
	}

	async fetchFleetHealth() {
		try {
			const res = await fetch(`${baseURL}/pratyaksa/fleet/health`).then((r) => r.json());
			this.fleetHealth = res.data;
			return res.data;
		} catch (e: any) {
			this.error = e?.message || 'Gagal fetch fleet health';
			return null;
		}
	}

	async fetchResult(assetId: string) {
		try {
			const res = await fetch(`${baseURL}/pratyaksa/result/${assetId}`).then((r) => r.json());
			return res.data;
		} catch {
			return null;
		}
	}

	async fetchExplain(predictionId: string) {
		try {
			const res = await fetch(`${baseURL}/pratyaksa/explain/${predictionId}`).then((r) => r.json());
			return res.data;
		} catch {
			return null;
		}
	}

	async setMode(mode: 'live' | 'simulasi' | 'auto') {
		const body = mode === 'auto' ? { reset: true } : { mode };
		const res = await fetch(`${baseURL}/pratyaksa/mode`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		}).then((r) => r.json());
		await this.fetchStatus();
		return res;
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

	setSourceMode(mode: SourceMode) {
		this.sourceMode = mode;
	}
}

export const pratyaksa = new PratyaksaStore();
