# Proyecto: Fundamentos de Programación con Python

## Descripción general
Proyecto de consola desarrollado en Python que aplica los conceptos fundamentales de programación:
variables, tipos de datos, condicionales, ciclos, funciones y manejo de archivos.
El aprendiz debe demostrar que entiende la lógica detrás de cada concepto, no solo que copió el código.

## Temas que el aprendiz debe dominar

### 1. Variables y tipos de datos
- Variables (int, float, str, bool)
- Conversión de tipos: `int()`, `float()`, `str()`
- Entrada del usuario con `input()`
- f-strings para formatear texto

### 2. Condicionales
- `if`, `elif`, `else`
- Operadores de comparación: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Operadores lógicos: `and`, `or`, `not`

### 3. Ciclos
- `for` con `range()`
- `while` con condición de parada
- `break` y `continue`
- Iterar sobre listas y cadenas

### 4. Funciones
- Definir funciones con `def`
- Parámetros y argumentos
- Valor de retorno con `return`
- Diferencia entre parámetro y argumento
- Alcance de variables (scope)

### 5. Listas y estructuras de datos
- Crear, acceder y modificar listas
- Métodos: `.append()`, `.remove()`, `.sort()`, `.len()`
- Diccionarios: claves y valores
- Recorrer listas con `for`

### 6. Manejo de errores
- `try` / `except` para capturar errores
- Errores comunes: `ValueError`, `ZeroDivisionError`, `IndexError`

### 7. Archivos (si aplica)
- Leer archivos con `open()` y modo `"r"`
- Escribir archivos con modo `"w"` y `"a"`
- Uso de `with open()` para cerrar automáticamente

## Ejemplos de proyectos típicos que sustenta un aprendiz
- Calculadora de consola con menú
- Sistema de registro de notas de estudiantes
- Juego de adivinanza de número
- Lista de compras o inventario básico
- Conversor de unidades (temperatura, moneda, etc.)

## Rúbrica de evaluación

| Criterio | Descripción |
|---|---|
| **Variables** | Usa los tipos correctos, sabe convertir entre ellos |
| **Condicionales** | Estructura correcta del if/elif/else, condiciones lógicas bien formadas |
| **Ciclos** | Sabe cuándo usar for vs while, evita ciclos infinitos |
| **Funciones** | Entiende el propósito de modularizar, usa return correctamente |
| **Explicación** | Puede explicar con sus palabras qué hace cada parte del código |

## Errores comunes que el evaluador debe explorar
- Confundir `=` (asignación) con `==` (comparación)
- No entender por qué `input()` siempre devuelve string
- Ciclos `while` sin condición de parada (ciclo infinito)
- No retornar valor en una función y usar `print()` en su lugar
- Variables globales cuando debería usar parámetros

## Preguntas sugeridas para la sustentación
- ¿Qué pasa si el usuario ingresa una letra donde se espera un número? ¿Cómo lo manejas?
- ¿Por qué usaste un `while` y no un `for` en esa parte?
- ¿Qué devuelve tu función `calcular()`? ¿Para qué sirve el `return`?
- Si tuvieras que guardar 100 estudiantes, ¿usarías 100 variables o qué usarías?
- ¿Qué diferencia hay entre una variable local y una global?
- ¿Qué significa que Python es "interpretado"?
- Si tu código tiene un error en la línea 15, ¿Python ejecuta las líneas 1 a 14?
- ¿Qué es un algoritmo? Dame un ejemplo de la vida real.
