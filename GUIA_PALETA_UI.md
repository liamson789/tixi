# Guía rápida de paleta UI (Tixi)

## Paleta oficial

- **Azul profundo**: `#0F172A`
- **Verde vibrante (acento principal)**: `#22C55E`
- **Blanco (fondo principal)**: `#FFFFFF`
- **Gris claro (superficies secundarias)**: `#F3F4F6`
- **Gris medio (texto secundario)**: `#6B7280`
- **Rojo advertencia/error**: `#EF4444`

## Regla principal

El rojo `#EF4444` se usa **solo** para:

- errores
- alertas críticas
- estados de número **vendido**

No usar rojo como color primario ni en botones primarios.

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
- Vendido: `#EF4444` + texto `#FFFFFF`
- Seleccionado / mío: `#0F172A` + texto `#FFFFFF`

### Feedback de sistema

- Éxito / confirmación de pago / progreso completado: `#22C55E`
- Error / alerta crítica: `#EF4444`

## Variables sugeridas (referencia)

```css
--brand-dark: #0F172A;
--brand-primary: #22C55E;
--brand-surface: #FFFFFF;
--brand-border: #F3F4F6;
--brand-muted: #6B7280;
--brand-danger: #EF4444;
```

## Checklist antes de publicar una vista

- ¿El fondo principal está en `#FFFFFF`?
- ¿Las acciones principales están en `#22C55E`?
- ¿Los títulos importantes usan `#0F172A`?
- ¿El texto secundario usa `#6B7280`?
- ¿El rojo `#EF4444` aparece solo en errores/alertas/vendidos?
