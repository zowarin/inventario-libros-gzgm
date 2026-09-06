import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/inventario/inventario-list/inventario-list.component').then(
        (m) => m.InventarioListComponent,
      ),
  },
  {
    path: 'inventario/nuevo',
    loadComponent: () =>
      import('./features/inventario/inventario-form/inventario-form.component').then(
        (m) => m.InventarioFormComponent,
      ),
  },
  {
    path: 'inventario/:id/editar',
    loadComponent: () =>
      import('./features/inventario/inventario-form/inventario-form.component').then(
        (m) => m.InventarioFormComponent,
      ),
  },
  {
    path: 'inventario/imprimir',
    loadComponent: () =>
      import('./features/inventario/imprimir-caja/imprimir-caja.component').then(
        (m) => m.ImprimirCajaComponent,
      ),
  },
  {
    path: 'inventario/imprimir-simple',
    loadComponent: () =>
      import('./features/inventario/imprimir-caja-simple/imprimir-caja-simple.component').then(
        (m) => m.ImprimirCajaSimpleComponent,
      ),
  },
];
