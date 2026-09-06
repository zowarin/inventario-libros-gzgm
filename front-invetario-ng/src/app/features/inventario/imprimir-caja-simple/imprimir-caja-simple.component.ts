import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { InventarioService } from '../inventario.service';
import { Inventario } from '../inventario.model';

@Component({
  selector: 'app-imprimir-caja-simple',
  imports: [RouterLink],
  templateUrl: './imprimir-caja-simple.component.html',
  styleUrl: './imprimir-caja-simple.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImprimirCajaSimpleComponent implements OnInit {
  private readonly service = inject(InventarioService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly cajas = this.service.cajas;
  protected readonly selectedCaja = signal('');
  protected readonly items = signal<Inventario[]>([]);
  protected readonly loading = signal(false);
  protected readonly fechaImpresion = signal('');

  protected readonly columnaIzquierda = computed(() =>
    this.items().slice(0, Math.ceil(this.items().length / 2)),
  );

  protected readonly columnaDerecha = computed(() =>
    this.items().slice(Math.ceil(this.items().length / 2)),
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

  protected tituloLibro(item: Inventario): string {
    return item.texto_ocr || item.titulo || item.archivo || `Libro #${item.id}`;
  }

  private async loadItems(caja: string): Promise<void> {
    this.loading.set(true);
    this.items.set(await this.service.getByCaja(caja));
    this.loading.set(false);
  }
}
