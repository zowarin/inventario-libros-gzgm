import { Injectable, inject, signal } from '@angular/core';
import { SupabaseService } from '../../core/supabase.service';
import { Inventario, InventarioInsert, InventarioUpdate } from './inventario.model';

const TABLE = 'inventario';

export interface InventarioQuery {
  page: number;
  pageSize: number;
  caja?: string;
  search?: string;
}

const SEARCH_COLUMNS = ['texto_ocr', 'titulo', 'album', 'archivo', 'carpeta'] as const;

@Injectable({ providedIn: 'root' })
export class InventarioService {
  private readonly supabase = inject(SupabaseService).client;

  readonly items = signal<Inventario[]>([]);
  readonly totalCount = signal(0);
  readonly cajas = signal<string[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  private requestId = 0;

  async load(query: InventarioQuery): Promise<void> {
    const requestId = ++this.requestId;
    this.loading.set(true);
    this.error.set(null);

    const { page, pageSize, caja, search } = query;
    const from = (page - 1) * pageSize;
    const to = from + pageSize - 1;

    let request = this.supabase
      .from(TABLE)
      .select('*', { count: 'exact' })
      .eq('eliminado', false)
      .order('id', { ascending: true })
      .range(from, to);

    if (caja) {
      request = request.eq('album', caja);
    }

    const term = search?.trim().replace(/[,()%]/g, ' ').trim();
    if (term) {
      const pattern = `%${term}%`;
      const filters = SEARCH_COLUMNS.map((col) => `${col}.ilike.${pattern}`);
      if (/^\d+$/.test(term)) {
        filters.push(`id.eq.${term}`);
      }
      request = request.or(filters.join(','));
    }

    const { data, error, count } = await request;

    // Ignore this response if a newer request has since been issued (out-of-order network replies).
    if (requestId !== this.requestId) {
      return;
    }

    if (error) {
      this.error.set(error.message);
    } else {
      this.items.set(data ?? []);
      this.totalCount.set(count ?? 0);
    }
    this.loading.set(false);
  }

  async loadCajas(): Promise<void> {
    const { data, error } = await this.supabase
      .from(TABLE)
      .select('album')
      .eq('eliminado', false)
      .not('album', 'is', null);

    if (!error && data) {
      const unique = Array.from(new Set(data.map((row) => row.album as string)));
      this.cajas.set(unique.sort((a, b) => a.localeCompare(b)));
    }
  }

  async getByCaja(caja: string): Promise<Inventario[]> {
    const { data, error } = await this.supabase
      .from(TABLE)
      .select('*')
      .eq('eliminado', false)
      .eq('album', caja)
      .order('id', { ascending: true });

    if (error) {
      this.error.set(error.message);
      return [];
    }
    return data ?? [];
  }

  async getById(id: number): Promise<Inventario | null> {
    const { data, error } = await this.supabase
      .from(TABLE)
      .select('*')
      .eq('id', id)
      .single();

    if (error) {
      this.error.set(error.message);
      return null;
    }
    return data;
  }

  async create(payload: InventarioInsert): Promise<Inventario | null> {
    this.error.set(null);
    const { data, error } = await this.supabase
      .from(TABLE)
      .insert(payload)
      .select()
      .single();

    if (error) {
      this.error.set(error.message);
      return null;
    }
    return data;
  }

  async update(id: number, payload: InventarioUpdate): Promise<Inventario | null> {
    this.error.set(null);
    const { data, error } = await this.supabase
      .from(TABLE)
      .update(payload)
      .eq('id', id)
      .select()
      .single();

    if (error) {
      this.error.set(error.message);
      return null;
    }
    return data;
  }

  async softDelete(id: number): Promise<boolean> {
    this.error.set(null);
    const { error } = await this.supabase.from(TABLE).update({ eliminado: true }).eq('id', id);

    if (error) {
      this.error.set(error.message);
      return false;
    }
    return true;
  }
}
