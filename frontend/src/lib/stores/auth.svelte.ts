/** Auth store — mirrors Nuxt `useAuth`. */
import { api } from '$lib/api';

export interface AuthUser {
	id: string;
	name: string;
	email: string;
	role: string;
	created_at: string;
}

class AuthStore {
	user = $state<AuthUser | null>(null);
	token = $state<string | null>(null);

	get isAuthenticated() {
		return !!this.token;
	}

	init() {
		if (typeof localStorage === 'undefined') return;
		const token = localStorage.getItem('auth_token');
		const userStr = localStorage.getItem('auth_user');
		if (token && userStr) {
			this.token = token;
			try {
				this.user = JSON.parse(userStr);
			} catch {
				this.clear();
			}
		}
	}

	private persist() {
		if (typeof localStorage === 'undefined') return;
		if (this.token) localStorage.setItem('auth_token', this.token);
		if (this.user) localStorage.setItem('auth_user', JSON.stringify(this.user));
	}

	async login(email: string, password: string) {
		const res: any = await api.login(email, password);
		this.token = res.data.token;
		this.user = res.data.user;
		this.persist();
		return res;
	}

	async register(name: string, email: string, password: string) {
		const res: any = await api.register(name, email, password);
		this.token = res.data.token;
		this.user = res.data.user;
		this.persist();
		return res;
	}

	clear() {
		this.token = null;
		this.user = null;
		if (typeof localStorage !== 'undefined') {
			localStorage.removeItem('auth_token');
			localStorage.removeItem('auth_user');
		}
	}
}

export const auth = new AuthStore();
