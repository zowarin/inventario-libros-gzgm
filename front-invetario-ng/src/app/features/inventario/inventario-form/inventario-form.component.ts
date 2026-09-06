import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { InventarioService } from '../inventario.service';

@Component({
  selector: 'app-inventario-form',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './inventario-form.component.html',
  styleUrl: './inventario-form.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InventarioFormComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  protected readonly service = inject(InventarioService);

  protected readonly itemId = signal<number | null>(null);
  protected readonly isEditMode = computed(() => this.itemId() !== null);
  protected readonly saving = signal(false);
  protected readonly deleting = signal(false);
  protected readonly formError = signal<string | null>(null);

  protected readonly form = this.fb.nonNullable.group({
    titulo: ['', Validators.required],
    album: [''],
    carpeta: [''],
    archivo: [''],
    portada: [''],
    rotacion: this.fb.control<number | null>(0),
    titulo_confianza: this.fb.control<number | null>(null),
    texto_ocr: [''],
    url_origen: [''],
  });

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (!idParam) {
      return;
    }

    const id = Number(idParam);
    this.itemId.set(id);

    void this.service.getById(id).then((item) => {
      if (!item) {
        this.formError.set('No se encontró el libro solicitado.');
        return;
      }
      this.form.setValue({
        titulo: item.titulo ?? '',
        album: item.album ?? '',
        carpeta: item.carpeta ?? '',
        archivo: item.archivo ?? '',
        portada: item.portada ?? '',
        rotacion: item.rotacion,
        titulo_confianza: item.titulo_confianza,
        texto_ocr: item.texto_ocr ?? '',
        url_origen: item.url_origen ?? '',
      });
    });
  }

  protected async onSubmit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    this.formError.set(null);

    const value = this.form.getRawValue();
    const payload = {
      titulo: value.titulo || null,
      album: value.album || null,
      carpeta: value.carpeta || null,
      archivo: value.archivo || null,
      portada: value.portada || null,
      rotacion: value.rotacion,
      titulo_confianza: value.titulo_confianza,
      texto_ocr: value.texto_ocr || null,
      url_origen: value.url_origen || null,
    };

    const id = this.itemId();
    const result = id === null
      ? await this.service.create(payload)
      : await this.service.update(id, payload);

    this.saving.set(false);

    if (!result) {
      this.formError.set(this.service.error() ?? 'No se pudo guardar el registro.');
      return;
    }

    void this.router.navigate(['/']);
  }

  protected async onDelete(): Promise<void> {
    const id = this.itemId();
    if (id === null) {
      return;
    }

    const confirmado = confirm('¿Eliminar este libro del inventario?');
    if (!confirmado) {
      return;
    }

    this.deleting.set(true);
    this.formError.set(null);

    const ok = await this.service.softDelete(id);

    this.deleting.set(false);

    if (!ok) {
      this.formError.set(this.service.error() ?? 'No se pudo eliminar el registro.');
      return;
    }

    void this.router.navigate(['/']);
  }
}
