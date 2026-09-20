"""Custom Gradio theme for Nivaas. Calm, editorial, utilitarian."""

import gradio as gr
from gradio.themes.utils import sizes, colors


class NivaasTheme(gr.themes.Base):
    def __init__(self) -> None:
        # Define custom teal color
        teal = gr.themes.Color(
            c50="#f0f7f6",
            c100="#d1e8e6",
            c200="#a3d1cc",
            c300="#75bab3",
            c400="#47a399",
            c500="#1F5F5B",
            c600="#1a5250",
            c700="#154544",
            c800="#103839",
            c900="#0b2b2d",
            c950="#062020",
        )

        neutral = gr.themes.Color(
            c50="#F7F6F2",
            c100="#edece8",
            c200="#D9D6CE",
            c300="#c5c2ba",
            c400="#9a978f",
            c500="#5B6068",
            c600="#4a4e55",
            c700="#393c42",
            c800="#1C1F23",
            c900="#151719",
            c950="#0d0e10",
        )

        super().__init__(
            primary_hue=teal,
            secondary_hue=teal,
            neutral_hue=neutral,
            radius_size=sizes.radius_sm,
            spacing_size=sizes.spacing_md,
            text_size=sizes.text_md,
        )
