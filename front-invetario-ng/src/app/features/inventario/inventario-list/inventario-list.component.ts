import { ChangeDetectionStrategy, Component, DestroyRef, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NgOptimizedImage, NgTemplateOutlet } from '@angular/common';
import { ActivatedRoute, Params, Router, RouterLink } from '@angular/router';
import { FsLightbox } from 'fslightbox-angular';
import { FotoConIdComponent } from '../../../shared/foto-con-id/foto-con-id.component';
import { InventarioService } from '../inventario.service';
import { Inventario } from '../inventario.model';

const DEFAULT_PAGE_SIZE = 20;
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];
const SEARCH_DEBOUNCE_MS = 350;

type ViewMode = 'table' | 'grid';

interface FiltrosUrl {
  page: number;
  pageSize: number;
  caja: string;
  q: string;
}

@Component({
  selector: 'app-inventario-list',
  imports: [RouterLink, NgOptimizedImage, NgTemplateOutlet, FsLightbox],
  templateUrl: './inventario-list.component.html',
  styleUrl: './inventario-list.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InventarioListComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly service = inject(InventarioService);

  protected readonly pageSizeOptions = PAGE_SIZE_OPTIONS;

  protected readonly page = signal(1);
  protected readonly pageSize = signal(DEFAULT_PAGE_SIZE);
  protected readonly selectedCaja = signal('');
  protected readonly searchTerm = signal('');
  protected readonly viewMode = signal<ViewMode>('table');

  protected readonly lightboxToggler = signal(false);
  protected readonly lightboxSlide = signal(1);
  protected readonly lightboxItems = computed(() =>
    this.service.items().filter((item) => !!this.portadaSrc(item)),
  );
  protected readonly lightboxSources = computed(() =>
    this.lightboxItems().map((item) => ({
      component: FotoConIdComponent,
      inputs: {
        src: this.portadaSrc(item) as string,
        id: item.id,
        caja: item.album,
        alt: `Portada de ${item.titulo || item.archivo || ''}`,
      },
    })),
  );

  protected readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.service.totalCount() / this.pageSize())),
  );

  protected readonly rangeStart = computed(() =>
    this.service.totalCount() === 0 ? 0 : (this.page() - 1) * this.pageSize() + 1,
  );

  protected readonly rangeEnd = computed(() =>
    Math.min(this.page() * this.pageSize(), this.service.totalCount()),
  );

  private searchDebounce?: ReturnType<typeof setTimeout>;

  ngOnInit(): void {
    void this.service.loadCajas();
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.page.set(this.parsePage(params.get('page')));
      this.pageSize.set(this.parsePageSize(params.get('pageSize')));
      this.selectedCaja.set(params.get('caja') ?? '');
      this.searchTerm.set(params.get('q') ?? '');
      void this.reload();
    });
  }

  ngOnDestroy(): void {
    clearTimeout(this.searchDebounce);
  }

  private parsePage(raw: string | null): number {
    const valor = Number(raw);
    return Number.isInteger(valor) && valor > 0 ? valor : 1;
  }

  private parsePageSize(raw: string | null): number {
    const valor = Number(raw);
    return PAGE_SIZE_OPTIONS.includes(valor) ? valor : DEFAULT_PAGE_SIZE;
  }

  private async reload(): Promise<void> {
    await this.service.load({
      page: this.page(),
      pageSize: this.pageSize(),
      caja: this.selectedCaja(),
      search: this.searchTerm(),
    });
  }

  /** Actualiza la URL con los filtros vigentes (mezclados con overrides); la
   *  navegacion resultante dispara la recarga via el subscribe de arriba, asi
   *  que la URL es la unica fuente de verdad del estado de filtros. */
  private actualizarUrl(overrides: Partial<FiltrosUrl>): void {
    const siguiente: FiltrosUrl = {
      page: overrides.page ?? this.page(),
      pageSize: overrides.pageSize ?? this.pageSize(),
      caja: overrides.caja ?? this.selectedCaja(),
      q: overrides.q ?? this.searchTerm(),
    };
    const queryParams: Params = {
      q: siguiente.q || null,
      caja: siguiente.caja || null,
      page: siguiente.page > 1 ? siguiente.page : null,
      pageSize: siguiente.pageSize !== DEFAULT_PAGE_SIZE ? siguiente.pageSize : null,
    };
    void this.router.navigate([], { relativeTo: this.route, queryParams, replaceUrl: true });
  }

  protected onCajaChange(event: Event): void {
    const caja = (event.target as HTMLSelectElement).value;
    this.actualizarUrl({ caja, page: 1 });
  }

  protected onSearchChange(event: Event): void {
    const q = (event.target as HTMLInputElement).value;
    clearTimeout(this.searchDebounce);
    this.searchDebounce = setTimeout(() => this.actualizarUrl({ q, page: 1 }), SEARCH_DEBOUNCE_MS);
  }

  protected onPageSizeChange(event: Event): void {
    const pageSize = Number((event.target as HTMLSelectElement).value);
    this.actualizarUrl({ pageSize, page: 1 });
  }

  protected goToPage(page: number): void {
    if (page < 1 || page > this.totalPages() || page === this.page()) {
      return;
    }
    this.actualizarUrl({ page });
  }

  protected portadaSrc(item: Inventario): string | null {
    return item.portada || null;
  }

  protected setViewMode(mode: ViewMode): void {
    this.viewMode.set(mode);
  }

  protected openLightbox(item: Inventario): void {
    const index = this.lightboxItems().findIndex((i) => i.id === item.id);
    if (index === -1) {
      return;
    }
    this.lightboxSlide.set(index + 1);
    this.lightboxToggler.update((value) => !value);
  }
}
