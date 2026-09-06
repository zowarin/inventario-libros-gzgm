import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-foto-con-id',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    style: 'display: flex; width: 100%; height: 100%; align-items: center; justify-content: center;',
  },
  template: `
    <div
      style="display: flex; flex-direction: column; align-items: center; gap: 8px; max-width: 100%; max-height: 100%;"
    >
      <span
        style="background: #facc15; color: #111827; font-weight: 700; font-size: 14px; line-height: 1; padding: 6px 14px; border-radius: 999px; font-variant-numeric: tabular-nums;"
      >
        @if (caja()) {
          {{ caja() }} · Id {{ id() }}
        } @else {
          Id {{ id() }}
        }
      </span>
      <img
        [src]="src()"
        [alt]="alt()"
        style="display: block; max-width: 100%; max-height: 80vh; width: auto; height: auto;"
      />
    </div>
  `,
})
export class FotoConIdComponent {
  readonly src = input.required<string>();
  readonly id = input.required<number>();
  readonly caja = input<string | null>(null);
  readonly alt = input('');
}
