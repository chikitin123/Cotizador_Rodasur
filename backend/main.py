from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, text
import urllib

app = FastAPI(title="API Cotizador Prueba")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ajusta SERVER y DATABASE si es necesario
params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=RODASUR;"
    "Trusted_Connection=yes;"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

class ItemCotizar(BaseModel):
    codigo: str
    marca: str = ""
    cantidad: int = 1

class SolicitudCotizacion(BaseModel):
    items: List[ItemCotizar]
    tipo_cliente: str = "NORMAL"

@app.get("/api/buscar")
def buscar_productos(q: str):
    query = text("""
        SELECT TOP 15 Codigo, Marca, Descripcion, StockLima, StockProvincia
        FROM MaestroProductos
        WHERE Codigo LIKE :q OR Descripcion LIKE :q OR Marca LIKE :q
    """)
    with engine.connect() as conn:
        resultados = conn.execute(query, {"q": f"%{q}%"}).mappings().all()
    return list(resultados)

@app.post("/api/cotizar")
def calcular_cotizacion(solicitud: SolicitudCotizacion):
    detalle_cotizado = []
    total_general = 0.0

    with engine.connect() as conn:
        for item in solicitud.items:
            sql = text("""
                SELECT Codigo, Marca, Descripcion, CostoBase, MargenPorcentaje, StockLima, StockProvincia
                FROM MaestroProductos
                WHERE Codigo = :cod AND (:marca = '' OR Marca = :marca)
            """)
            prod = conn.execute(sql, {
                "cod": item.codigo.strip().upper(),
                "marca": item.marca.strip().upper()
            }).mappings().first()

            if not prod:
                detalle_cotizado.append({
                    "codigo": item.codigo,
                    "marca": item.marca,
                    "descripcion": "CÓDIGO NO ENCONTRADO",
                    "cantidad": item.cantidad,
                    "precio_unit": 0.0,
                    "subtotal": 0.0,
                    "stock_total": 0
                })
                continue

            costo = float(prod["CostoBase"])
            margen = float(prod["MargenPorcentaje"])

            if solicitud.tipo_cliente == "MAYORISTA":
                margen = margen * 0.85
            if item.cantidad >= 50:
                margen = margen * 0.90

            precio_sin_igv = costo * (1 + margen)
            precio_con_igv = round(precio_sin_igv * 1.18, 2)
            subtotal = round(precio_con_igv * item.cantidad, 2)
            total_general += subtotal

            detalle_cotizado.append({
                "codigo": prod["Codigo"],
                "marca": prod["Marca"],
                "descripcion": prod["Descripcion"],
                "cantidad": item.cantidad,
                "precio_unit": precio_con_igv,
                "subtotal": subtotal,
                "stock_total": prod["StockLima"] + prod["StockProvincia"]
            })

    return {
        "items": detalle_cotizado,
        "total_con_igv": round(total_general, 2)
    }