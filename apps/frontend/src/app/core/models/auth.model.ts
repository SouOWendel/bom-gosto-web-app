export interface User {
	id: number;
	username: string;
	email: string;
	firstName: string;
	lastName: string;
}

export interface Credentials {
	username: string;
	password: string;
}

export interface AuthResponse {
	access: string;
	refresh?: string;
	user: User;
}