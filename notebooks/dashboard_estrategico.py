"""Dashboard Estrategico - Benchmark 360 ISP Ecuador.

Genera visualizaciones de alto impacto para el equipo de Marketing
y Estrategia de Producto de Netlife.

Ejecutar:
    uv run python notebooks/dashboard_estrategico.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.patheffects as patheffects
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "visualizations"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Brand colors (consistent across all charts)
BRAND_COLORS = {
    "Netlife": "#E8491D",
    "Xtrim": "#1B2A4A",
    "Claro": "#DA291C",
    "Ecuanet": "#F5A623",
    "Alfanet": "#2ECC71",
    "Fibramax": "#8E44AD",
    "CNT": "#3498DB",
    "Celerity": "#1ABC9C",
}

BG_DARK = "#0D1117"
BG_CARD = "#161B22"
TEXT_LIGHT = "#E6EDF3"
TEXT_MUTED = "#8B949E"
GRID_COLOR = "#21262D"
ACCENT_GOLD = "#F0B429"
NETLIFE_RED = "#E8491D"

plt.rcParams.update({
    "figure.facecolor": BG_DARK,
    "axes.facecolor": BG_CARD,
    "axes.edgecolor": GRID_COLOR,
    "axes.labelcolor": TEXT_LIGHT,
    "text.color": TEXT_LIGHT,
    "xtick.color": TEXT_MUTED,
    "ytick.color": TEXT_MUTED,
    "grid.color": GRID_COLOR,
    "grid.alpha": 0.3,
    "font.family": "sans-serif",
    "font.size": 11,
})


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
def load_benchmark() -> pd.DataFrame:
    df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "benchmark_industria.csv")
    df["valor_por_mega"] = df["precio_plan"] / df["velocidad_download_mbps"]
    # Remove duplicates (Claro has a dup)
    df = df.drop_duplicates(subset=["marca", "nombre_plan", "velocidad_download_mbps"])
    return df


def load_market_share() -> list[dict]:
    path = Path("/Users/jeanpierregarcia/Downloads/porcentaje (1).json")
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Chart 1: Valor por Mega — Competitive Intelligence
# ---------------------------------------------------------------------------
def chart_valor_por_mega(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(18, 8), gridspec_kw={"width_ratios": [1.2, 1]})
    fig.suptitle(
        "BENCHMARK 360  |  Valor por Megabit ($USD / Mbps)",
        fontsize=18, fontweight="bold", color=TEXT_LIGHT, y=0.97,
    )
    fig.text(
        0.5, 0.93,
        "Cuanto menor el valor, mejor la propuesta para el cliente",
        ha="center", fontsize=11, color=TEXT_MUTED, style="italic",
    )

    # --- Left: Average value per mega by ISP ---
    ax1 = axes[0]
    avg = df.groupby("marca")["valor_por_mega"].mean().sort_values()
    min_val = df.groupby("marca")["valor_por_mega"].min().reindex(avg.index)

    colors_avg = [BRAND_COLORS.get(m, "#555") for m in avg.index]
    y_pos = np.arange(len(avg))

    # Min bars (background)
    bars_min = ax1.barh(
        y_pos, min_val.values, height=0.55,
        color=[BRAND_COLORS.get(m, "#555") for m in avg.index],
        alpha=0.3, label="Mejor plan (min)",
    )

    # Avg bars (foreground)
    bars_avg = ax1.barh(
        y_pos, avg.values, height=0.35,
        color=colors_avg, alpha=0.95, label="Promedio",
        edgecolor="white", linewidth=0.5,
    )

    # Labels
    for i, (v_avg, v_min) in enumerate(zip(avg.values, min_val.values)):
        ax1.text(
            v_avg + 0.002, i, f"${v_avg:.3f}",
            va="center", fontsize=10, fontweight="bold", color=TEXT_LIGHT,
        )
        ax1.text(
            v_min + 0.001, i + 0.25, f"min ${v_min:.3f}",
            va="center", fontsize=8, color=ACCENT_GOLD,
        )

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(avg.index, fontsize=12, fontweight="bold")
    ax1.set_xlabel("USD por Mbps (menor = mejor)", fontsize=11)
    ax1.set_title(
        "Promedio y Mejor Plan por ISP",
        fontsize=13, fontweight="bold", pad=10,
    )
    ax1.legend(loc="lower right", fontsize=9, framealpha=0.3)
    ax1.grid(axis="x", alpha=0.2)
    ax1.set_xlim(0, avg.max() * 1.35)

    # Highlight Netlife
    for i, marca in enumerate(avg.index):
        if marca == "Netlife":
            ax1.get_yticklabels()[i].set_color(NETLIFE_RED)
            ax1.get_yticklabels()[i].set_fontsize(13)

    # --- Right: Scatter plot — Price vs Speed (bubble = apps included) ---
    ax2 = axes[1]

    for marca in df["marca"].unique():
        subset = df[df["marca"] == marca]
        color = BRAND_COLORS.get(marca, "#888")
        sizes = (subset["pys_adicionales"].fillna(0) + 1) * 60

        ax2.scatter(
            subset["velocidad_download_mbps"],
            subset["precio_plan"],
            s=sizes,
            c=color,
            alpha=0.8,
            label=marca,
            edgecolors="white",
            linewidth=0.5,
            zorder=3,
        )

    # Reference line: best value (frontier)
    frontier = df.sort_values("velocidad_download_mbps")
    best_vals = []
    current_min_ratio = float("inf")
    for _, row in frontier.iterrows():
        ratio = row["precio_plan"] / row["velocidad_download_mbps"]
        if ratio < current_min_ratio:
            current_min_ratio = ratio
            best_vals.append(row)
    if best_vals:
        bv = pd.DataFrame(best_vals).sort_values("velocidad_download_mbps")
        ax2.plot(
            bv["velocidad_download_mbps"], bv["precio_plan"],
            "--", color=ACCENT_GOLD, alpha=0.5, linewidth=1.5,
            label="Frontera eficiente",
        )

    ax2.set_xlabel("Velocidad (Mbps)", fontsize=11)
    ax2.set_ylabel("Precio mensual (USD sin IVA)", fontsize=11)
    ax2.set_title(
        "Precio vs Velocidad (burbuja = servicios incluidos)",
        fontsize=13, fontweight="bold", pad=10,
    )
    ax2.legend(
        loc="upper left", fontsize=8, framealpha=0.3,
        ncol=2, markerscale=0.6,
    )
    ax2.grid(alpha=0.15)

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    path = OUTPUT_DIR / "01_valor_por_mega.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


# ---------------------------------------------------------------------------
# Chart 2: Strategic Positioning Map
# ---------------------------------------------------------------------------
def chart_posicionamiento(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 9))

    fig.suptitle(
        "MAPA DE POSICIONAMIENTO COMPETITIVO",
        fontsize=18, fontweight="bold", color=TEXT_LIGHT, y=0.97,
    )
    fig.text(
        0.5, 0.93,
        "Cada burbuja es un plan  |  Tamano = servicios incluidos  |  Objetivo: cuadrante inferior-derecho",
        ha="center", fontsize=10, color=TEXT_MUTED, style="italic",
    )

    # Quadrant lines
    med_speed = df["velocidad_download_mbps"].median()
    med_price_mega = df["valor_por_mega"].median()
    ax.axvline(med_speed, color=TEXT_MUTED, linestyle="--", alpha=0.3, linewidth=1)
    ax.axhline(med_price_mega, color=TEXT_MUTED, linestyle="--", alpha=0.3, linewidth=1)

    # Quadrant labels
    ax.text(
        200, df["valor_por_mega"].max() * 0.95,
        "BAJO VALOR\nBaja velocidad, alto costo/Mbps",
        fontsize=8, color="#E74C3C", alpha=0.6, ha="center",
    )
    ax.text(
        1000, df["valor_por_mega"].max() * 0.95,
        "PREMIUM\nAlta velocidad, alto costo/Mbps",
        fontsize=8, color=ACCENT_GOLD, alpha=0.6, ha="center",
    )
    ax.text(
        200, df["valor_por_mega"].min() * 1.1,
        "ECONOMICO\nBaja velocidad, bajo costo/Mbps",
        fontsize=8, color=TEXT_MUTED, alpha=0.6, ha="center",
    )
    ax.text(
        1000, df["valor_por_mega"].min() * 1.1,
        "MEJOR PROPUESTA\nAlta velocidad, bajo costo/Mbps",
        fontsize=8, color="#2ECC71", alpha=0.7, ha="center", fontweight="bold",
    )

    for marca in df["marca"].unique():
        subset = df[df["marca"] == marca]
        color = BRAND_COLORS.get(marca, "#888")
        sizes = (subset["pys_adicionales"].fillna(0) + 1) * 80

        ax.scatter(
            subset["velocidad_download_mbps"],
            subset["valor_por_mega"],
            s=sizes,
            c=color,
            alpha=0.85,
            label=marca,
            edgecolors="white",
            linewidth=0.8,
            zorder=3,
        )

        # Label top plans
        for _, row in subset.iterrows():
            if row["velocidad_download_mbps"] >= 800 or row["valor_por_mega"] < 0.025:
                ax.annotate(
                    row["nombre_plan"],
                    (row["velocidad_download_mbps"], row["valor_por_mega"]),
                    textcoords="offset points",
                    xytext=(8, 6),
                    fontsize=7,
                    color=color,
                    alpha=0.9,
                )

    ax.set_xlabel("Velocidad de descarga (Mbps)", fontsize=12)
    ax.set_ylabel("Costo por Mbps (USD / Mbps)", fontsize=12)
    ax.legend(
        loc="upper right", fontsize=9, framealpha=0.3,
        title="ISP", title_fontsize=10,
    )
    ax.grid(alpha=0.15)
    ax.invert_yaxis()  # Lower cost/Mbps = better = top

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    path = OUTPUT_DIR / "02_posicionamiento_competitivo.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


# ---------------------------------------------------------------------------
# Chart 3: Ecuador Map — Netlife Market Share by Province
# ---------------------------------------------------------------------------
def chart_mapa_ecuador(market_data: list[dict]) -> None:
    try:
        import geopandas as gpd
    except ImportError:
        print("  [SKIP] geopandas not installed, skipping map")
        return

    # Build province dataframe
    rows = []
    for entry in market_data:
        prov = entry["province"]
        if prov == "Nacional (Promedio)":
            continue
        for s in entry["shares"]:
            rows.append({
                "province": prov,
                "brand": s["brand"],
                "percentage": s["percentage"],
            })
    share_df = pd.DataFrame(rows)

    # Netlife share per province
    netlife = share_df[share_df["brand"] == "Netlife"][["province", "percentage"]].copy()
    netlife.columns = ["province", "netlife_pct"]

    # Leader per province
    leaders = share_df.loc[
        share_df.groupby("province")["percentage"].idxmax()
    ][["province", "brand", "percentage"]].copy()
    leaders.columns = ["province", "leader", "leader_pct"]

    prov_df = netlife.merge(leaders, on="province", how="left")

    # Load Ecuador GeoJSON (GADM 4.1 — has valid geometry for all provinces)
    try:
        geo = gpd.read_file(
            "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_ECU_1.json",
        )
    except Exception:
        print("  [SKIP] Could not load Ecuador GeoJSON")
        return

    geo = geo.rename(columns={"NAME_1": "geo_province"})

    # Normalize names — GADM joins multi-word names (e.g. "ElOro", "LosRios")
    import unicodedata
    import re

    def normalize(s):
        if not isinstance(s, str):
            return ""
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        # Insert space before uppercase letters to split GADM names
        s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
        return s.lower().strip()

    geo["_norm"] = geo["geo_province"].apply(normalize)
    prov_df["_norm"] = prov_df["province"].apply(normalize)

    # Align GADM names → JSON names
    name_map = {
        "santo domingodelos tsachilas": "santo domingo",
        "santo domingo de los tsachilas": "santo domingo",
    }
    geo["_norm"] = geo["_norm"].replace(name_map)
    prov_df["_norm"] = prov_df["_norm"].replace(name_map)

    geo = geo.merge(prov_df, on="_norm", how="left")

    # --- Plot ---
    fig, axes = plt.subplots(1, 2, figsize=(20, 12))
    fig.suptitle(
        "MAPA ESTRATEGICO DE ECUADOR  |  Market Share por Provincia",
        fontsize=18, fontweight="bold", color=TEXT_LIGHT, y=0.97,
    )

    # Left: Netlife percentage
    ax1 = axes[0]
    ax1.set_facecolor(BG_DARK)

    geo.plot(
        column="netlife_pct",
        ax=ax1,
        legend=True,
        cmap="YlOrRd",
        edgecolor="#333",
        linewidth=0.5,
        missing_kwds={"color": "#2a2a2a", "edgecolor": "#444"},
        legend_kwds={
            "label": "% Market Share Netlife",
            "orientation": "horizontal",
            "shrink": 0.6,
            "pad": 0.05,
        },
    )

    # Province labels
    for _, row in geo.iterrows():
        if row.geometry and not pd.isna(row.get("netlife_pct")):
            centroid = row.geometry.centroid
            label = f"{row.get('province', '')}\n{row.get('netlife_pct', 0):.0f}%"
            ax1.annotate(
                label, (centroid.x, centroid.y),
                fontsize=6, ha="center", color=TEXT_LIGHT,
                fontweight="bold",
                path_effects=[
                    patheffects.withStroke(
                        linewidth=2, foreground="black",
                    ),
                ],
            )

    ax1.set_title(
        "Netlife: Participacion de Mercado (%)",
        fontsize=14, fontweight="bold", color=NETLIFE_RED, pad=10,
    )
    ax1.axis("off")

    # Right: Who leads each province
    ax2 = axes[1]
    ax2.set_facecolor(BG_DARK)

    # Color by leader brand
    leader_color_map = {}
    for _, row in geo.iterrows():
        leader = row.get("leader", "")
        if leader == "Netlife":
            leader_color_map[row.get("_norm", "")] = NETLIFE_RED
        elif leader == "Xtrim":
            leader_color_map[row.get("_norm", "")] = BRAND_COLORS["Xtrim"]
        elif leader == "CNT":
            leader_color_map[row.get("_norm", "")] = BRAND_COLORS["CNT"]
        elif "Claro" in str(leader):
            leader_color_map[row.get("_norm", "")] = BRAND_COLORS["Claro"]
        else:
            leader_color_map[row.get("_norm", "")] = "#555"

    geo["leader_color"] = geo["_norm"].map(leader_color_map).fillna("#2a2a2a")

    geo.plot(
        ax=ax2,
        color=geo["leader_color"],
        edgecolor="#333",
        linewidth=0.5,
    )

    for _, row in geo.iterrows():
        if row.geometry and not pd.isna(row.get("leader")):
            centroid = row.geometry.centroid
            label = f"{row.get('province', '')}\n{row.get('leader', '')} {row.get('leader_pct', 0):.0f}%"
            ax2.annotate(
                label, (centroid.x, centroid.y),
                fontsize=6, ha="center", color=TEXT_LIGHT,
                fontweight="bold",
                path_effects=[
                    patheffects.withStroke(
                        linewidth=2, foreground="black",
                    ),
                ],
            )

    ax2.set_title(
        "Lider del Mercado por Provincia",
        fontsize=14, fontweight="bold", pad=10,
    )
    ax2.axis("off")

    # Legend for leaders
    import matplotlib.patches as mpatches
    legend_patches = [
        mpatches.Patch(color=NETLIFE_RED, label="Netlife lidera"),
        mpatches.Patch(color=BRAND_COLORS["Xtrim"], label="Xtrim lidera"),
        mpatches.Patch(color=BRAND_COLORS["CNT"], label="CNT lidera"),
        mpatches.Patch(color=BRAND_COLORS["Claro"], label="Claro lidera"),
    ]
    ax2.legend(
        handles=legend_patches, loc="lower left",
        fontsize=9, framealpha=0.3,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    path = OUTPUT_DIR / "03_mapa_ecuador.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


# ---------------------------------------------------------------------------
# Chart 4: Semantic Analysis — Competitive Arsenal
# ---------------------------------------------------------------------------
def chart_analisis_semantico(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    fig.suptitle(
        "ANALISIS ESTRATEGICO  |  Arsenal Competitivo de los ISPs",
        fontsize=18, fontweight="bold", color=TEXT_LIGHT, y=0.98,
    )

    # --- (0,0) Streaming services per ISP ---
    ax = axes[0, 0]
    streaming_map = {
        "disney_plus": "Disney+",
        "hbo": "HBO",
        "zapping": "Zapping",
        "liga_ecuabet": "Liga Ecuabet",
        "paramount_plus": "Paramount+",
        "netlife_play": "Netlife Play",
    }

    svc_matrix = []
    for _, row in df.iterrows():
        try:
            detail = json.loads(row["pys_adicionales_detalle"].replace("'", '"')) if isinstance(row["pys_adicionales_detalle"], str) and row["pys_adicionales_detalle"] not in ("{}", "") else {}
        except Exception:
            detail = {}
        for svc_key, svc_label in streaming_map.items():
            if svc_key in detail:
                svc_matrix.append({
                    "marca": row["marca"],
                    "plan": row["nombre_plan"],
                    "servicio": svc_label,
                })

    if svc_matrix:
        svc_df = pd.DataFrame(svc_matrix)
        pivot = svc_df.groupby(["marca", "servicio"]).size().unstack(fill_value=0)

        # Heatmap
        brands = pivot.index.tolist()
        services = pivot.columns.tolist()
        data_matrix = pivot.values

        im = ax.imshow(data_matrix, cmap="YlOrRd", aspect="auto", vmin=0)
        ax.set_xticks(range(len(services)))
        ax.set_xticklabels(services, rotation=45, ha="right", fontsize=9)
        ax.set_yticks(range(len(brands)))
        ax.set_yticklabels(brands, fontsize=10, fontweight="bold")

        for i in range(len(brands)):
            for j in range(len(services)):
                val = data_matrix[i, j]
                if val > 0:
                    ax.text(
                        j, i, f"{int(val)}",
                        ha="center", va="center",
                        fontsize=11, fontweight="bold",
                        color="white" if val > 2 else TEXT_LIGHT,
                    )

    ax.set_title(
        "Servicios de Streaming por ISP (# planes que incluyen)",
        fontsize=12, fontweight="bold", pad=10,
    )

    # --- (0,1) Price range per ISP ---
    ax = axes[0, 1]
    marcas_sorted = df.groupby("marca")["precio_plan"].median().sort_values().index

    for i, marca in enumerate(marcas_sorted):
        subset = df[df["marca"] == marca]
        prices = subset["precio_plan"].values
        color = BRAND_COLORS.get(marca, "#888")

        ax.scatter(
            [i] * len(prices), prices,
            s=80, c=color, alpha=0.8, edgecolors="white", linewidth=0.5,
            zorder=3,
        )
        ax.plot(
            [i, i], [prices.min(), prices.max()],
            color=color, linewidth=3, alpha=0.4, zorder=2,
        )
        # Min/max labels
        ax.text(
            i + 0.2, prices.min(), f"${prices.min():.0f}",
            fontsize=8, color=ACCENT_GOLD, va="top",
        )
        ax.text(
            i + 0.2, prices.max(), f"${prices.max():.0f}",
            fontsize=8, color=TEXT_MUTED, va="bottom",
        )

    ax.set_xticks(range(len(marcas_sorted)))
    ax.set_xticklabels(marcas_sorted, fontsize=10, fontweight="bold", rotation=20)
    ax.set_ylabel("Precio mensual (USD sin IVA)")
    ax.set_title(
        "Rango de Precios por ISP (min - max)",
        fontsize=12, fontweight="bold", pad=10,
    )
    ax.grid(axis="y", alpha=0.15)

    # --- (1,0) Speed tiers offered ---
    ax = axes[1, 0]
    speed_bins = [0, 300, 600, 900, 1200]
    speed_labels = ["<300", "300-600", "600-900", "900+"]
    df["speed_tier"] = pd.cut(
        df["velocidad_download_mbps"], bins=speed_bins, labels=speed_labels,
    )

    tier_counts = df.groupby(["marca", "speed_tier"], observed=False).size().unstack(fill_value=0)
    tier_counts = tier_counts.reindex(columns=speed_labels, fill_value=0)

    x = np.arange(len(tier_counts.index))
    width = 0.18
    for j, tier in enumerate(speed_labels):
        vals = tier_counts[tier].values
        colors = [BRAND_COLORS.get(m, "#888") for m in tier_counts.index]
        alpha = 0.4 + 0.2 * j
        ax.bar(
            x + j * width, vals, width,
            color=colors, alpha=alpha, edgecolor="white", linewidth=0.3,
        )
        for i, v in enumerate(vals):
            if v > 0:
                ax.text(
                    x[i] + j * width, v + 0.1, str(int(v)),
                    ha="center", fontsize=8, color=TEXT_LIGHT,
                )

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(tier_counts.index, fontsize=10, fontweight="bold", rotation=20)
    ax.set_ylabel("# Planes")
    ax.set_title(
        "Distribucion de Velocidades por ISP",
        fontsize=12, fontweight="bold", pad=10,
    )

    # Legend for tiers
    import matplotlib.patches as mpatches
    tier_legend = [
        mpatches.Patch(color="#888", alpha=0.4 + 0.2 * j, label=tier)
        for j, tier in enumerate(speed_labels)
    ]
    ax.legend(handles=tier_legend, fontsize=8, loc="upper right", framealpha=0.3)
    ax.grid(axis="y", alpha=0.15)

    # --- (1,1) Strategic scorecard ---
    ax = axes[1, 1]
    ax.axis("off")

    # Compute scores per ISP
    scorecard = []
    for marca in df["marca"].unique():
        subset = df[df["marca"] == marca]
        avg_valor_mega = subset["valor_por_mega"].mean()
        min_valor_mega = subset["valor_por_mega"].min()
        max_speed = subset["velocidad_download_mbps"].max()
        avg_apps = subset["pys_adicionales"].fillna(0).mean()
        n_plans = len(subset)
        has_discount = (subset["descuento"].fillna(0) > 0).any()
        free_install = (subset["costo_instalacion"].fillna(999) == 0).any()

        scorecard.append({
            "ISP": marca,
            "Plans": n_plans,
            "Max Mbps": f"{max_speed:.0f}",
            "$/Mbps avg": f"${avg_valor_mega:.3f}",
            "$/Mbps best": f"${min_valor_mega:.3f}",
            "Apps avg": f"{avg_apps:.1f}",
            "Dcto": "Si" if has_discount else "No",
            "Install $0": "Si" if free_install else "No",
        })

    sc_df = pd.DataFrame(scorecard).sort_values("$/Mbps avg")
    cols = sc_df.columns.tolist()

    table = ax.table(
        cellText=sc_df.values,
        colLabels=cols,
        cellLoc="center",
        loc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(list(range(len(cols))))

    # Style
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(GRID_COLOR)
        if row == 0:
            cell.set_facecolor("#1F2937")
            cell.set_text_props(color=ACCENT_GOLD, fontweight="bold", fontsize=9)
            cell.set_height(0.08)
        else:
            cell.set_facecolor(BG_CARD)
            cell.set_text_props(color=TEXT_LIGHT)
            cell.set_height(0.065)
            # Highlight Netlife row
            isp_name = sc_df.iloc[row - 1]["ISP"]
            if isp_name == "Netlife":
                cell.set_facecolor("#2D1810")
                cell.set_text_props(color=NETLIFE_RED, fontweight="bold")

    ax.set_title(
        "Scorecard Competitivo",
        fontsize=14, fontweight="bold", pad=20,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    path = OUTPUT_DIR / "04_analisis_estrategico.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("BENCHMARK 360 — Dashboard Estrategico")
    print("=" * 60)

    print("\nCargando datos...")
    df = load_benchmark()
    market_data = load_market_share()
    print(f"  {len(df)} planes, {df['marca'].nunique()} ISPs")

    print("\nGenerando visualizaciones...")
    chart_valor_por_mega(df)
    chart_posicionamiento(df)
    chart_mapa_ecuador(market_data)
    chart_analisis_semantico(df)

    print(f"\nTodos los graficos guardados en: {OUTPUT_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
