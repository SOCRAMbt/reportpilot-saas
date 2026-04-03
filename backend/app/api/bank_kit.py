"""
API Bank-Kit - Generación de paquetes para banco

Genera automáticamente:
- Libro IVA Ventas (PDF)
- Libro IVA Compras (PDF)
- Constancia de Inscripción (PDF o placeholder)

Empaquetado en ZIP para descarga.
"""

import io
import logging
import zipfile
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Cliente, Comprobante, Tenant
from app.api.auth import get_current_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank-kit", tags=["bank-kit"])


@router.get("/{cliente_id}/generar")
async def generar_bank_kit(
    cliente_id: int,
    periodo: str = Query(..., description="Período en formato YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Generar paquete para banco (Libro IVA + Constancia)

    - **cliente_id**: ID del cliente
    - **periodo**: Período a exportar (YYYY-MM)
    """
    # Validar período
    try:
        anio, mes = map(int, periodo.split("-"))
        if not (1 <= mes <= 12):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail="Período inválido. Usar YYYY-MM")

    # Obtener cliente
    resultado = await db.execute(
        select(Cliente).where(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id
        )
    )
    cliente = resultado.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Obtener tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    # Fechas del período
    fecha_desde = datetime(anio, mes, 1).date()
    if mes == 12:
        fecha_hasta = datetime(anio + 1, 1, 1).date()
    else:
        fecha_hasta = datetime(anio, mes + 1, 1).date()

    # Obtener comprobantes del período
    comprobantes_result = await db.execute(
        select(Comprobante).where(
            Comprobante.cliente_id == cliente_id,
            Comprobante.fecha_emision >= fecha_desde,
            Comprobante.fecha_emision < fecha_hasta,
            Comprobante.estado_interno == "INCORPORADO"
        ).order_by(Comprobante.fecha_emision)
    )
    comprobantes = comprobantes_result.scalars().all()

    # Separar emitidos y recibidos
    comprobantes_emitidos = [c for c in comprobantes if c.tipo_comprobante in ["1", "2", "3", "A", "B", "C"]]
    comprobantes_recibidos = [c for c in comprobantes if c.cuit_emisor != cliente.cuit]

    # Generar PDFs
    buffer_zip = io.BytesIO()

    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Libro IVA Ventas
        pdf_ventas = generar_libro_iva_ventas(
            tenant, cliente, comprobantes_emitidos, periodo
        )
        zip_file.writestr(f"Libro_IVA_Ventas_{periodo}.pdf", pdf_ventas)

        # 2. Libro IVA Compras
        pdf_compras = generar_libro_iva_compras(
            tenant, cliente, comprobantes_recibidos, periodo
        )
        zip_file.writestr(f"Libro_IVA_Compras_{periodo}.pdf", pdf_compras)

        # 3. Constancia de Inscripción (placeholder)
        pdf_constancia = generar_constancia_inscripcion(tenant, cliente)
        zip_file.writestr(f"Constancia_Inscripcion_{cliente.cuit}.pdf", pdf_constancia)

    buffer_zip.seek(0)

    # Nombre del archivo ZIP
    nombre_archivo = f"BankKit_{cliente.razon_social.replace(' ', '_')}_{periodo}.zip"

    return StreamingResponse(
        buffer_zip,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"}
    )


def generar_libro_iva_ventas(
    tenant: Tenant,
    cliente: Cliente,
    comprobantes: list,
    periodo: str
) -> bytes:
    """
    Generar Libro IVA Ventas en PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    elementos = []
    styles = getSampleStyleSheet()

    # Título
    titulo_style = ParagraphStyle(
        "Titulo",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=1,
        spaceAfter=12
    )
    elementos.append(Paragraph(f"LIBRO IVA VENTAS - {periodo}", titulo_style))

    # Datos del contribuyente
    datos_style = ParagraphStyle(
        "Datos",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6
    )
    elementos.append(Paragraph(f"<b>Razón Social:</b> {cliente.razon_social}", datos_style))
    elementos.append(Paragraph(f"<b>CUIT:</b> {cliente.cuit}", datos_style))
    elementos.append(Paragraph(f"<b>Período:</b> {periodo}", datos_style))
    elementos.append(Spacer(1, 0.5*cm))

    # Tabla de comprobantes
    datos_tabla = [["Fecha", "Tipo", "Pto Vta", "Número", "CUIT Receptor", "Neto Gravado", "IVA 21%", "IVA 10.5%", "Percepciones", "Total"]]

    total_neto = Decimal(0)
    total_iva_21 = Decimal(0)
    total_iva_105 = Decimal(0)
    total_percepciones = Decimal(0)
    total_general = Decimal(0)

    for cbte in comprobantes:
        # Determinar tipo de comprobante
        tipos = {"1": "FA", "2": "FB", "3": "FC", "A": "FA", "B": "FB", "C": "FC", "6": "NC", "7": "NCB", "8": "NCC"}
        tipo_cbte = tipos.get(str(cbte.tipo_comprobante), cbte.tipo_comprobante)

        # Calcular IVA desglosado (simplificado: 21% y 10.5%)
        neto = Decimal(str(cbte.neto_gravado or 0))
        iva = Decimal(str(cbte.iva or 0))
        total = Decimal(str(cbte.total or 0))

        # Asumir 21% por defecto (simplificación)
        iva_21 = iva * Decimal("0.7")  # 70% del IVA es 21%
        iva_105 = iva * Decimal("0.3")  # 30% del IVA es 10.5%
        percepciones = Decimal(str(cbte.percepcion_iibb or 0)) + Decimal(str(cbte.percepcion_iva or 0))

        datos_tabla.append([
            cbte.fecha_emision.isoformat() if cbte.fecha_emision else "",
            tipo_cbte,
            str(cbte.punto_venta),
            str(cbte.numero).zfill(8),
            cbte.cuit_receptor or "-",
            f"${neto:,.2f}",
            f"${iva_21:,.2f}",
            f"${iva_105:,.2f}",
            f"${percepciones:,.2f}",
            f"${total:,.2f}"
        ])

        total_neto += neto
        total_iva_21 += iva_21
        total_iva_105 += iva_105
        total_percepciones += percepciones
        total_general += total

    # Fila de totales
    datos_tabla.append([
        "", "", "", "", "<b>TOTALES</b>",
        f"<b>${total_neto:,.2f}</b>",
        f"<b>${total_iva_21:,.2f}</b>",
        f"<b>${total_iva_105:,.2f}</b>",
        f"<b>${total_percepciones:,.2f}</b>",
        f"<b>${total_general:,.2f}</b>"
    ])

    # Crear tabla
    tabla = Table(datos_tabla, colWidths=[2*cm, 1*cm, 1*cm, 1.5*cm, 2.5*cm, 2*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2*cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.whitesmoke]),
    ]))

    elementos.append(tabla)

    # Pie de página
    elementos.append(Spacer(1, 1*cm))
    elementos.append(Paragraph(f"<i>Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", styles["Italic"]))

    # Construir PDF
    doc.build(elementos)

    return buffer.getvalue()


def generar_libro_iva_compras(
    tenant: Tenant,
    cliente: Cliente,
    comprobantes: list,
    periodo: str
) -> bytes:
    """
    Generar Libro IVA Compras en PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    elementos = []
    styles = getSampleStyleSheet()

    # Título
    titulo_style = ParagraphStyle(
        "Titulo",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=1,
        spaceAfter=12
    )
    elementos.append(Paragraph(f"LIBRO IVA COMPRAS - {periodo}", titulo_style))

    # Datos del contribuyente
    datos_style = ParagraphStyle(
        "Datos",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6
    )
    elementos.append(Paragraph(f"<b>Razón Social:</b> {cliente.razon_social}", datos_style))
    elementos.append(Paragraph(f"<b>CUIT:</b> {cliente.cuit}", datos_style))
    elementos.append(Paragraph(f"<b>Período:</b> {periodo}", datos_style))
    elementos.append(Spacer(1, 0.5*cm))

    # Tabla de comprobantes
    datos_tabla = [["Fecha", "Tipo", "Pto Vta", "Número", "CUIT Emisor", "Neto Gravado", "IVA 21%", "IVA 10.5%", "Percepciones", "Total"]]

    total_neto = Decimal(0)
    total_iva_21 = Decimal(0)
    total_iva_105 = Decimal(0)
    total_percepciones = Decimal(0)
    total_general = Decimal(0)

    for cbte in comprobantes:
        tipos = {"1": "FA", "2": "FB", "3": "FC", "A": "FA", "B": "FB", "C": "FC", "6": "NC", "7": "NCB", "8": "NCC"}
        tipo_cbte = tipos.get(str(cbte.tipo_comprobante), cbte.tipo_comprobante)

        neto = Decimal(str(cbte.neto_gravado or 0))
        iva = Decimal(str(cbte.iva or 0))
        total = Decimal(str(cbte.total or 0))

        iva_21 = iva * Decimal("0.7")
        iva_105 = iva * Decimal("0.3")
        percepciones = Decimal(str(cbte.percepcion_iibb or 0)) + Decimal(str(cbte.percepcion_iva or 0))

        datos_tabla.append([
            cbte.fecha_emision.isoformat() if cbte.fecha_emision else "",
            tipo_cbte,
            str(cbte.punto_venta),
            str(cbte.numero).zfill(8),
            cbte.cuit_emisor or "-",
            f"${neto:,.2f}",
            f"${iva_21:,.2f}",
            f"${iva_105:,.2f}",
            f"${percepciones:,.2f}",
            f"${total:,.2f}"
        ])

        total_neto += neto
        total_iva_21 += iva_21
        total_iva_105 += iva_105
        total_percepciones += percepciones
        total_general += total

    # Fila de totales
    datos_tabla.append([
        "", "", "", "", "<b>TOTALES</b>",
        f"<b>${total_neto:,.2f}</b>",
        f"<b>${total_iva_21:,.2f}</b>",
        f"<b>${total_iva_105:,.2f}</b>",
        f"<b>${total_percepciones:,.2f}</b>",
        f"<b>${total_general:,.2f}</b>"
    ])

    tabla = Table(datos_tabla, colWidths=[2*cm, 1*cm, 1*cm, 1.5*cm, 2.5*cm, 2*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2*cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.whitesmoke]),
    ]))

    elementos.append(tabla)

    elementos.append(Spacer(1, 1*cm))
    elementos.append(Paragraph(f"<i>Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", styles["Italic"]))

    doc.build(elementos)

    return buffer.getvalue()


def generar_constancia_inscripcion(tenant: Tenant, cliente: Cliente) -> bytes:
    """
    Generar constancia de inscripción (placeholder)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    elementos = []
    styles = getSampleStyleSheet()

    # Título
    titulo_style = ParagraphStyle(
        "Titulo",
        parent=styles["Heading1"],
        fontSize=14,
        alignment=1,
        spaceAfter=20
    )
    elementos.append(Paragraph("CONSTANCIA DE INSCRIPCIÓN", titulo_style))

    # Contenido
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=10,
        alignment=0
    )

    elementos.append(Paragraph(f"<b>CUIT:</b> {cliente.cuit}", body_style))
    elementos.append(Paragraph(f"<b>Razón Social:</b> {cliente.razon_social}", body_style))
    elementos.append(Paragraph(f"<b>Categoría:</b> {cliente.categoria_monotributo or 'No determinada'}", body_style))
    elementos.append(Spacer(1, 1*cm))

    elementos.append(Paragraph(
        "Este documento es un comprobante generado automáticamente por AccountantOS. "
        "Para la constancia oficial, consulte el sitio web de ARCA/AFIP.",
        body_style
    ))

    elementos.append(Spacer(1, 2*cm))
    elementos.append(Paragraph(f"<i>Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", styles["Italic"]))

    doc.build(elementos)

    return buffer.getvalue()
