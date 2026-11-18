# componentes/alarma.py
# Franja de alarma de posible celo. Aparece arriba en todas las pantallas
# y parpadea (como el buzzer intermitente) mientras la alarma está activa.

import flet as ft
import config


class BannerAlarma:

    def __init__(self, al_silenciar):
        self.encendida = False
        self.texto = ft.Text("", size=14, color="#FFFFFF", weight=ft.FontWeight.BOLD, expand=True)
        self.boton = ft.Button(
            content="Silenciar buzzer",
            icon=ft.Icons.VOLUME_OFF,
            on_click=al_silenciar,     # Evento: equivale al command de Tkinter
            bgcolor="#FFFFFF",
            color=config.ROJO,
        )
        self.control = ft.Container(
            visible=False,
            padding=ft.Padding.symmetric(horizontal=18, vertical=12),
            border_radius=12,
            bgcolor=config.ROJO,
            animate_opacity=300,
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#FFFFFF", size=28),
                          self.texto, self.boton],
            ),
        )

    def actualizar(self, datos):
        activa = datos["alarma"]
        self.control.visible = activa
        if not activa:
            self.control.opacity = 1
            return
        self.texto.value = f"Posible celo en la vaca 01 · razón {datos['razon']:.2f} (umbral {datos['umbral_celo']:.2f})"
        self.boton.visible = not datos["buzzer_silenciado"]
        # Parpadeo: alterna la opacidad en cada actualización mientras el buzzer suena
        if datos["buzzer_sonando"]:
            self.encendida = not self.encendida
            self.control.opacity = 1 if self.encendida else 0.55
        else:
            self.control.opacity = 1
