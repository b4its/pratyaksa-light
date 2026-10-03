/**
 * API layer — mirrors the Nuxt `useApi` composable.
 * Base URL from PUBLIC_API_BASE (default http://localhost:8114/api/v1).
 */
import { env } from '$env/dynamic/public';

const baseURL = env.PUBLIC_API_BASE || 'http://localhost:8114/api/v1';

function getToken(): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem('auth_token');
}

export function authHeaders(): Record<string, string> {
	const token = getToken();
	return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T = any>(
	path: string,
	opts: { method?: string; body?: any; auth?: boolean; headers?: Record<string, string> } = {}
): Promise<T> {
	const { method = 'GET', body, auth = false, headers = {} } = opts;
	const finalHeaders: Record<string, string> = { ...headers };
	if (auth) Object.assign(finalHeaders, authHeaders());
	let payload: any = body;
	if (body !== undefined && !(body instanceof FormData)) {
		finalHeaders['Content-Type'] = 'application/json';
		payload = JSON.stringify(body);
	}
	const res = await fetch(`${baseURL}${path}`, { method, headers: finalHeaders, body: payload });
	const text = await res.text();
	let data: any = null;
	if (text) {
		try {
			data = JSON.parse(text);
		} catch {
			// Non-JSON body (e.g. an HTML error page from a proxy). Keep it as
			// a string so the message below is still meaningful.
			data = { message: text.slice(0, 200) };
		}
	}
	if (!res.ok) {
		const message = data?.message || data?.detail || `HTTP ${res.status}`;
		throw new Error(message);
	}
	return data as T;
}

function qs(params: Record<string, any>): string {
	const q = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) {
		if (v !== undefined && v !== null && v !== '') q.set(k, String(v));
	}
	const s = q.toString();
	return s ? `?${s}` : '';
}

export const api = {
	baseURL,
	// Auth
	login: (email: string, password: string) =>
		request('/auth/login', { method: 'POST', body: { email, password } }),
	register: (name: string, email: string, password: string) =>
		request('/auth/register', { method: 'POST', body: { name, email, password } }),
	me: () => request('/auth/me', { auth: true }),

	// Dashboard
	getDashboardStats: () => request('/dashboard', { auth: true }),

	// Jenis alat berat
	getJenisAlatBerat: (params?: { page?: number; per_page?: number; search?: string }) =>
		request(`/jenis-alat-berat${qs(params || {})}`, { auth: true }),
	createJenisAlatBerat: (body: { nama: string; deskripsi?: string }) =>
		request('/jenis-alat-berat', { method: 'POST', body, auth: true }),
	updateJenisAlatBerat: (id: string, body: { nama?: string; deskripsi?: string }) =>
		request(`/jenis-alat-berat/${id}`, { method: 'PUT', body, auth: true }),
	deleteJenisAlatBerat: (id: string) =>
		request(`/jenis-alat-berat/${id}`, { method: 'DELETE', auth: true }),

	// Unit tambang
	getUnitTambang: (params?: {
		page?: number;
		per_page?: number;
		search?: string;
		status?: string;
		jenis_alat_berat_id?: string;
	}) => request(`/unit-tambang${qs(params || {})}`, { auth: true }),
	createUnitTambang: (body: any) =>
		request('/unit-tambang', { method: 'POST', body, auth: true }),
	updateUnitTambang: (id: string, body: any) =>
		request(`/unit-tambang/${id}`, { method: 'PUT', body, auth: true }),
	deleteUnitTambang: (id: string) =>
		request(`/unit-tambang/${id}`, { method: 'DELETE', auth: true }),

	// Upload model 3D (backend /svc)
	uploadModel: (file: File) => {
		const fd = new FormData();
		fd.append('file', file);
		return request('/svc/upload-model', { method: 'POST', body: fd });
	},
	sendAlert: (payload: Record<string, string>) =>
		request('/svc/send-alert', { method: 'POST', body: payload }),

	// Analisa kerusakan (health analytics)
	getAnalisaOverview: () => request('/analisa/overview', { auth: true }),
	getUnitAnalysis: (id: string) => request(`/analisa/unit/${id}`, { auth: true }),

	// Work orders
	getWorkOrders: (params?: { page?: number; per_page?: number; wo_status?: string; asset_code?: string }) =>
		request(`/work-orders${qs(params || {})}`, { auth: true }),
	getWorkOrder: (id: string) => request(`/work-orders/${id}`, { auth: true }),
	createWorkOrder: (body: any) => request('/work-orders', { method: 'POST', body, auth: true }),
	updateWorkOrder: (id: string, body: any) =>
		request(`/work-orders/${id}`, { method: 'PUT', body, auth: true }),

	// Telemetry
	getTelemetryHistory: (unitId: string, limit = 100) =>
		request(`/telemetry/unit/${unitId}?limit=${limit}`, { auth: true }),
	postTelemetry: (body: Record<string, any>) =>
		request('/telemetry', { method: 'POST', body, auth: true }),

	// Analisa manual (MongoDB)
	getAnalisa: (params?: {
		page?: number;
		per_page?: number;
		unit_tambang_id?: string;
		severity?: string;
		status_analisa?: string;
	}) => request(`/analisa${qs(params || {})}`, { auth: true }),
	createAnalisa: (body: any) => request('/analisa', { method: 'POST', body, auth: true }),
	updateAnalisa: (id: string, body: any) =>
		request(`/analisa/${id}`, { method: 'PUT', body, auth: true }),
	deleteAnalisa: (id: string) => request(`/analisa/${id}`, { method: 'DELETE', auth: true })
};
