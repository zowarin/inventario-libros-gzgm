import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { NgOptimizedImage } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FsLightbox } from 'fslightbox-angular';
import { FotoConIdComponent } from '../../../shared/foto-con-id/foto-con-id.component';
import { InventarioService } from '../inventario.service';
import { Inventario } from '../inventario.model';

@Component({
  selector: 'app-imprimir-caja',
  imports: [RouterLink, NgOptimizedImage, FsLightbox],
  templateUrl: './imprimir-caja.component.html',
  styleUrl: './imprimir-caja.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImprimirCajaComponent implements OnInit {
  private readonly service = inject(InventarioService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly cajas = this.service.cajas;
  protected readonly selectedCaja = signal('');
  protected readonly items = signal<Inventario[]>([]);
  protected readonly loading = signal(false);
  protected readonly fechaImpresion = signal('');

  protected readonly lightboxToggler = signal(false);
  protected readonly lightboxSlide = signal(1);
  protected readonly lightboxItems = computed(() =>
    this.items().filter((item) => !!this.portadaSrc(item)),
  );
  protected readonly lightboxSources = computed(() =>
    this.lightboxItems().map((item) => ({
      component: FotoConIdComponent,
      inputs: {
        src: this.portadaSrc(item) as string,
        id: item.id,
        caja: item.album,
        alt: `Portada de ${this.tituloLibro(item)}`,
      },
    })),
  );

  ngOnInit(): void {
    void this.service.loadCajas();

    this.fechaImpresion.set(
      new Date().toLocaleDateString('es', { year: 'numeric', month: 'long', day: 'numeric' }),
    );

    const cajaParam = this.route.snapshot.queryParamMap.get('caja') ?? '';
    if (cajaParam) {
      this.selectedCaja.set(cajaParam);
      void this.loadItems(cajaParam);
    }
  }

  protected onCajaChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.selectedCaja.set(value);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { caja: value || null },
      queryParamsHandling: 'merge',
    });

    if (value) {
      void this.loadItems(value);
    } else {
      this.items.set([]);
    }
  }

  protected imprimir(): void {
    window.print();
  }

  protected portadaSrc(item: Inventario): string | null {
    return item.portada || null;
  }

  protected tituloLibro(item: Inventario): string {
    return item.texto_ocr || item.titulo || item.archivo || `Libro #${item.id}`;
  }

  protected openLightbox(item: Inventario): void {
    const index = this.lightboxItems().findIndex((i) => i.id === item.id);
    if (index === -1) {
      return;
    }
    this.lightboxSlide.set(index + 1);
    this.lightboxToggler.update((value) => !value);
  }

  private async loadItems(caja: string): Promise<void> {
    this.loading.set(true);
    this.items.set(await this.service.getByCaja(caja));
    this.loading.set(false);
  }
}
