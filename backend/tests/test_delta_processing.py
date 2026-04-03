"""
Tests de Delta-Processing v9.7
"""

import pytest
from datetime import date
from decimal import Decimal

from app.services.delta_processing import (
    calcular_hash_delta,
    comparar_comprobantes,
    EstadosComprobante,
)


def test_calcular_hash_delta():
    """Test de cálculo de hash delta"""
    hash1 = calcular_hash_delta("20123456789", 1, 123456)
    hash2 = calcular_hash_delta("20123456789", 1, 123456)
    hash3 = calcular_hash_delta("20987654321", 1, 123456)

    assert hash1 == hash2  # Mismos datos = mismo hash
    assert hash1 != hash3  # Diferente CUIT = diferente hash
    assert len(hash1) == 64  # SHA-256 = 64 caracteres hex


def test_comparar_comprobantes_iguales():
    """Test de comparación - comprobantes iguales"""
    existente = type(
        "ComprobanteMock",
        (),
        {
            "cuit_emisor": "20123456789",
            "punto_venta": 1,
            "numero": 123456,
            "tipo_comprobante": "A",
            "total": Decimal("1210.00"),
            "fecha_emision": date(2026, 3, 28),
        },
    )()

    nuevo = {
        "cuit_emisor": "20123456789",
        "punto_venta": 1,
        "numero": 123456,
        "tipo_comprobante": "A",
        "total": 1210.00,
        "fecha_emision": "2026-03-28",
    }

    son_iguales, discrepancias = comparar_comprobantes(existente, nuevo)

    assert son_iguales
    assert len(discrepancias) == 0


def test_comparar_comprobantes_diferencia_total():
    """Test de comparación - diferencia en total"""
    existente = type(
        "ComprobanteMock",
        (),
        {
            "cuit_emisor": "20123456789",
            "punto_venta": 1,
            "numero": 123456,
            "tipo_comprobante": "A",
            "total": Decimal("1210.00"),
            "fecha_emision": date(2026, 3, 28),
        },
    )()

    # Diferencia mayor al 1%
    nuevo = {
        "cuit_emisor": "20123456789",
        "punto_venta": 1,
        "numero": 123456,
        "tipo_comprobante": "A",
        "total": 1500.00,  # >1% de diferencia
        "fecha_emision": "2026-03-28",
    }

    son_iguales, discrepancias = comparar_comprobantes(existente, nuevo)

    assert not son_iguales
    assert any("Total" in d for d in discrepancias)


def test_comparar_comprobantes_tolerancia_1_por_ciento():
    """Test de tolerancia del 1% en total"""
    existente = type(
        "ComprobanteMock",
        (),
        {
            "cuit_emisor": "20123456789",
            "punto_venta": 1,
            "numero": 123456,
            "tipo_comprobante": "A",
            "total": Decimal("1000.00"),
            "fecha_emision": date(2026, 3, 28),
        },
    )()

    # Diferencia exacta del 1% (debería pasar)
    nuevo = {
        "cuit_emisor": "20123456789",
        "punto_venta": 1,
        "numero": 123456,
        "tipo_comprobante": "A",
        "total": 1009.00,  # 0.9% de diferencia
        "fecha_emision": "2026-03-28",
    }

    son_iguales, discrepancias = comparar_comprobantes(existente, nuevo)

    # Con 0.9% de diferencia, debería considerar iguales
    assert son_iguales
