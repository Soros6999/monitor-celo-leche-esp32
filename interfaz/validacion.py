# validacion.py
# Validación de los datos que el usuario escribe en los campos de texto.
#
# Cada función recibe el texto tal como lo escribió el usuario y devuelve
# una tupla (valor, error):
#   - si el dato es válido:   (número, None)
#   - si no lo es:            (None, "mensaje que explica qué corregir")
# Así la vista puede mostrar el error debajo del campo y no enviar el comando.


def validar_decimal(texto, minimo, maximo, nombre="El valor", incluir_minimo=True):
    """Valida un número decimal dentro de un rango.

    Acepta coma o punto como separador decimal ("1,8" o "1.8"),
    porque en Colombia se escribe con coma.
    """
    texto = (texto or "").strip().replace(",", ".")
    if texto == "":
        return None, f"{nombre} es obligatorio"
    try:
        valor = float(texto)
    except ValueError:
        return None, "Escriba solo números, por ejemplo 1.8"
    if valor != valor or valor in (float("inf"), float("-inf")):   # NaN o infinito
        return None, "Escriba un número válido"
    if incluir_minimo and valor < minimo:
        return None, f"Debe ser como mínimo {minimo:g}"
    if not incluir_minimo and valor <= minimo:
        return None, f"Debe ser mayor que {minimo:g}"
    if valor > maximo:
        return None, f"Debe ser como máximo {maximo:g}"
    return valor, None
