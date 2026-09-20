export interface User {
	login: string;
	primeiro_acesso: boolean;
}

export interface Credentials {
	login: string;
	senha: string;
}

export interface AuthResponse {
	autenticado: boolean;
	login: string;
	primeiro_acesso: boolean;
}

export interface ChangePasswordResponse {
	detail: string;
	primeiro_acesso: boolean;
}