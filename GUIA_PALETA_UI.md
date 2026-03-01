# Guía rápida de paleta UI (Tixi)

## Paleta oficial

- **Azul profundo**: `#0F172A`
- **Verde vibrante (acento principal)**: `#22C55E`
- **Blanco (fondo principal)**: `#FFFFFF`
- **Gris claro (superficies secundarias)**: `#F3F4F6`
- **Gris medio (texto secundario)**: `#6B7280`
- **Verde de feedback/estados**: `#22C55E`

## Regla principal

El verde `#22C55E` se usa para:

- confirmaciones
- alertas
- estados de número **vendido**

Usar verde como color principal y de estado en toda la interfaz.

## Uso por componente

### Navegación y estructura

- Navbar / header / footer: `#0F172A`
- Títulos importantes: `#0F172A`
- Fondo general del sitio: `#FFFFFF`

### Botones y acciones

- Botón principal (ej. “Participar”, “Reservar números”): `#22C55E`
- Hover de botón principal: mantener `#22C55E` o una variación mínima dentro del mismo tono
- Botones secundarios: fondo `#FFFFFF` o `#F3F4F6`, texto `#0F172A`

### Cards y contenedores

- Card / panel secundario: fondo o borde en `#F3F4F6`
- Contenido destacado dentro de card: texto `#0F172A`

### Texto

- Texto principal: `#0F172A`
- Texto secundario / descripción: `#6B7280`

### Estados de rifas / números

- Disponible: `#FFFFFF` + borde `#F3F4F6`
- Reservado: `#F3F4F6` + texto `#6B7280`
- Vendido: `#22C55E` + texto `#FFFFFF`
- Seleccionado / mío: `#0F172A` + texto `#FFFFFF`

### Feedback de sistema

- Éxito / confirmación de pago / progreso completado: `#22C55E`
- Alertas y feedback: `#22C55E`

## Variables sugeridas (referencia)

```css
--brand-dark: #0F172A;
--brand-primary: #22C55E;
--brand-surface: #FFFFFF;
--brand-border: #F3F4F6;
--brand-muted: #6B7280;
--brand-danger: #22C55E;
```

## Checklist antes de publicar una vista

- ¿El fondo principal está en `#FFFFFF`?
- ¿Las acciones principales están en `#22C55E`?
- ¿Los títulos importantes usan `#0F172A`?
- ¿El texto secundario usa `#6B7280`?
- ¿Los estados y alertas usan `#22C55E`?
