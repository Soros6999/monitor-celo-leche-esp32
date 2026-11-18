# main.py
# Punto de entrada de la interfaz gráfica.
#
# Ejecutar desde la carpeta interfaz/:
#     python main.py
#
# Flet llama a main(page) cuando la ventana está lista; aquí solo se crea
# la aplicación. Toda la lógica vive en las clases.

import flet as ft
from app import AplicacionMonitor


def main(page: ft.Page):
    AplicacionMonitor(page)


if __name__ == "__main__":
    ft.run(main)
