import { DOCUMENT } from '@angular/common';
import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, finalize, map, of, shareReplay } from 'rxjs';

// servico para garantir que o cookie csrf esteja presente antes de operacoes que alteram dados
@Injectable({ providedIn: 'root' })
export class CsrfService {
    private readonly http = inject(HttpClient);
    private readonly document = inject(DOCUMENT);
    private tokenRequest: Observable<string> | null = null;

    // prepara o cookie csrf antes de operacoes que alteram dados
    ensureToken(): Observable<string> {
        const cookieToken = this.readCookie();
        if (cookieToken) {
            return of(cookieToken);
        }

        if (!this.tokenRequest) {
            this.tokenRequest = this.http
                .get<{ csrf_token: string }>('/api/auth/csrf/', { withCredentials: true })
                .pipe(
                    map(() => {
                        const token = this.readCookie();
                        if (!token) {
                            throw new Error('A API nao retornou o cookie CSRF esperado.');
                        }
                        return token;
                    }),
                    finalize(() => {
                        this.tokenRequest = null;
                    }),
                    shareReplay({ bufferSize: 1, refCount: false }),
                );
        }

        return this.tokenRequest;
    }

    // le o cookie csrf do documento
    private readCookie(): string | null {
        const cookie = this.document.cookie
            .split(';')
            .map((part) => part.trim())
            .find((part) => part.startsWith('csrftoken='));

        return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : null;
    }
}
