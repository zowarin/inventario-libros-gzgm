import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { NgOptimizedImage, NgTemplateOutlet } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FsLightbox } from 'fslightbox-angular';
import { FotoConIdComponent } from '../../../shared/foto-con-id/foto-con-id.component';
import { InventarioService } from '../inventario.service';
import { Inventario } from '../inventario.model';

const DEFAULT_PAGE_SIZE = 20;
const SEARCH_DEBOUNCE_MS = 350;

type ViewMode = 'table' | 'grid';

@Component({
  selector: 'app-inventario-list',
  imports: [RouterLink, NgOptimizedImage, NgTemplateOutlet, FsLightbox],
  templateUrl: './inventario-list.component.html',
  styleUrl: './inventario-list.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InventarioListComponent implements OnInit, OnDestroy {
  protected readonly service = inject(InventarioService);

  protected readonly pageSizeOptions = [10, 20, 50, 100];

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
    void this.reload();
  }

  ngOnDestroy(): void {
    clearTimeout(this.searchDebounce);
  }

  private async reload(): Promise<void> {
    await this.service.load({
      page: this.page(),
      pageSize: this.pageSize(),
      caja: this.selectedCaja(),
      search: this.searchTerm(),
    });
  }

  protected onCajaChange(event: Event): void {
    this.selectedCaja.set((event.target as HTMLSelectElement).value);
    this.page.set(1);
    void this.reload();
  }

  protected onSearchChange(event: Event): void {
    this.searchTerm.set((event.target as HTMLInputElement).value);
    this.page.set(1);
    clearTimeout(this.searchDebounce);
    this.searchDebounce = setTimeout(() => void this.reload(), SEARCH_DEBOUNCE_MS);
  }

  protected onPageSizeChange(event: Event): void {
    this.pageSize.set(Number((event.target as HTMLSelectElement).value));
    this.page.set(1);
    void this.reload();
  }

  protected goToPage(page: number): void {
    if (page < 1 || page > this.totalPages() || page === this.page()) {
      return;
    }
    this.page.set(page);
    void this.reload();
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
