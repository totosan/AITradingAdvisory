"""Shared HTML snippets for chart-related assets."""

LIGHTWEIGHT_CHARTS_LOCAL_SRC = "/static/vendor/lightweight-charts.standalone.production.js"
LIGHTWEIGHT_CHARTS_CDN_SRC = "https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"

# Always use CDN for iframe compatibility - local paths don't work in iframes served from different origins
LIGHTWEIGHT_CHARTS_SCRIPT = (
    f'<script src="{LIGHTWEIGHT_CHARTS_CDN_SRC}"></script>\n'
    '<script>\n'
    '    // Verify LightweightCharts loaded correctly\n'
    '    if (typeof window.LightweightCharts === "undefined") {\n'
    '        console.error("LightweightCharts failed to load from CDN!");\n'
    '        document.body.innerHTML = "<h2 style=\\"color:red;padding:20px;\\">Chart library failed to load. Please refresh.</h2>";\n'
    '    } else {\n'
    '        console.log("LightweightCharts loaded successfully, version:", LightweightCharts.version());\n'
    '    }\n'
    '</script>'
)

__all__ = [
    "LIGHTWEIGHT_CHARTS_LOCAL_SRC",
    "LIGHTWEIGHT_CHARTS_CDN_SRC",
    "LIGHTWEIGHT_CHARTS_SCRIPT",
]
