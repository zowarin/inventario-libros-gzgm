export interface Inventario {
  id: number;
  portada: string | null;
  titulo: string | null;
  album: string | null;
  carpeta: string | null;
  archivo: string | null;
  rotacion: number | null;
  titulo_confianza: number | null;
  texto_ocr: string | null;
  url_origen: string | null;
  eliminado: boolean;
  created_at: string;
}

export type InventarioInsert = Omit<Inventario, 'id' | 'created_at' | 'eliminado'>;

export type InventarioUpdate = Partial<InventarioInsert>;
