"""Shared HTML snippets for chart-related assets."""

LIGHTWEIGHT_CHARTS_LOCAL_SRC = "/static/vendor/lightweight-charts.standalone.production.js"
LIGHTWEIGHT_CHARTS_CDN_SRC = "https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"

LIGHTWEIGHT_CHARTS_SCRIPT = (
    f'<script src="{LIGHTWEIGHT_CHARTS_LOCAL_SRC}"></script>\n'
    '<script>\n'
    '    if (typeof window.LightweightCharts === "undefined") {\n'
    f'        document.write(\'<script src="{LIGHTWEIGHT_CHARTS_CDN_SRC}"><\\/script>\');\n'
    '    }\n'
    '</script>'
)

__all__ = [
    "LIGHTWEIGHT_CHARTS_LOCAL_SRC",
    "LIGHTWEIGHT_CHARTS_CDN_SRC",
    "LIGHTWEIGHT_CHARTS_SCRIPT",
]
