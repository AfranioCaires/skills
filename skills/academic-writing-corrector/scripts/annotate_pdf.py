#!/usr/bin/env python3
"""
annotate_pdf.py — Adiciona comentários visuais em um PDF acadêmico usando PyMuPDF (fitz).

Uso:
    python annotate_pdf.py --input documento.pdf --comments comentarios.json --output saida_comentada.pdf

Schema do JSON de comentários: ver references/schema_comentarios.json
"""

import json
import argparse
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Instale PyMuPDF: pip install pymupdf --break-system-packages")
    sys.exit(1)


# Mapeamento de categoria → cor RGBA (vermelho, verde, azul, alfa)
CORES = {
    "CRÍTICO":     (1.0, 0.2, 0.2),   # Vermelho
    "IMPORTANTE":  (1.0, 0.6, 0.1),   # Laranja
    "SUGESTÃO":    (1.0, 0.9, 0.1),   # Amarelo
    "POSITIVO":    (0.2, 0.8, 0.3),   # Verde
    "INFORMAÇÃO":  (0.2, 0.6, 1.0),   # Azul
}

SIMBOLOS = {
    "CRÍTICO":    "❌",
    "IMPORTANTE": "⚠️",
    "SUGESTÃO":   "💡",
    "POSITIVO":   "✅",
    "INFORMAÇÃO": "ℹ️",
}


def add_margin_comment(page, comentario: dict, y_offset: float, margin_x: float):
    """Adiciona uma caixa de comentário na margem direita da página."""
    categoria = comentario.get("categoria", "INFORMAÇÃO").upper()
    texto = comentario.get("texto", "")
    simbolo = SIMBOLOS.get(categoria, "ℹ️")
    cor = CORES.get(categoria, (0.5, 0.5, 0.5))

    page_rect = page.rect
    margin_width = min(160, page_rect.width * 0.30)
    box_x0 = page_rect.width - margin_width - 5
    box_y0 = y_offset
    box_height = 60
    box_x1 = page_rect.width - 5
    box_y1 = box_y0 + box_height

    # Caixa de fundo com cor da categoria
    rect = fitz.Rect(box_x0, box_y0, box_x1, box_y1)
    fill_color = (*cor, 0.15)  # transparência
    border_color = cor

    # Desenha retângulo colorido
    shape = page.new_shape()
    shape.draw_rect(rect)
    shape.finish(color=border_color, fill=(*cor, 0.12), width=1.2)
    shape.commit()

    # Cabeçalho (categoria)
    header = f"{simbolo} {categoria}"
    page.insert_text(
        fitz.Point(box_x0 + 4, box_y0 + 11),
        header,
        fontsize=6.5,
        color=cor,
    )

    # Texto do comentário (quebra automática simplificada)
    palavras = texto.split()
    linhas = []
    linha_atual = []
    for palavra in palavras:
        linha_atual.append(palavra)
        if len(" ".join(linha_atual)) > 28:
            linhas.append(" ".join(linha_atual[:-1]))
            linha_atual = [palavra]
    if linha_atual:
        linhas.append(" ".join(linha_atual))

    for i, linha in enumerate(linhas[:4]):  # máximo 4 linhas
        page.insert_text(
            fitz.Point(box_x0 + 4, box_y0 + 22 + i * 10),
            linha,
            fontsize=6,
            color=(0.1, 0.1, 0.1),
        )

    # Linha conectora da margem ao texto (opcional, posição estimada)
    trecho = comentario.get("trecho_referencia", "")
    if trecho:
        # Tenta encontrar o trecho na página para desenhar seta
        rects = page.search_for(trecho[:40])
        if rects:
            alvo = rects[0]
            shape = page.new_shape()
            shape.draw_line(
                fitz.Point(box_x0, (box_y0 + box_y1) / 2),
                fitz.Point(alvo.x1, alvo.y0 + alvo.height / 2),
            )
            shape.finish(color=(*cor, 0.5), width=0.7, dashes="[2 2] 0")
            shape.commit()

    return box_y1 + 6  # próxima posição Y disponível


def annotate_pdf(input_path: str, comments_path: str, output_path: str):
    """Abre o PDF, adiciona comentários por página e salva."""

    with open(comments_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    comentarios_por_pagina: dict[int, list] = {}
    for c in data.get("comentarios", []):
        pag = c.get("pagina", 1)
        comentarios_por_pagina.setdefault(pag, []).append(c)

    doc = fitz.open(input_path)

    # Adiciona rodapé de legenda na primeira página
    primeira = doc[0]
    legenda_y = primeira.rect.height - 20
    legenda_texto = "  ".join([f"{s} {cat}" for cat, s in SIMBOLOS.items()])
    primeira.insert_text(
        fitz.Point(10, legenda_y),
        f"Legenda: {legenda_texto}",
        fontsize=5.5,
        color=(0.4, 0.4, 0.4),
    )

    for pag_num, comentarios in comentarios_por_pagina.items():
        if pag_num > len(doc):
            continue
        page = doc[pag_num - 1]

        # Posição Y inicial dos comentários na margem (começa no topo com margem)
        y_pos = 20.0
        for comentario in comentarios:
            y_pos = add_margin_comment(page, comentario, y_pos, margin_x=10)
            if y_pos > page.rect.height - 30:
                break  # evita ultrapassar a página

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    print(f"✅ PDF comentado salvo em: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adiciona comentários acadêmicos a um PDF")
    parser.add_argument("--input", required=True, help="PDF de entrada")
    parser.add_argument("--comments", required=True, help="JSON com os comentários")
    parser.add_argument("--output", required=True, help="PDF de saída comentado")
    args = parser.parse_args()

    annotate_pdf(args.input, args.comments, args.output)
