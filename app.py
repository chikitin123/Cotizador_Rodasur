import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(
    page_title="Cotizador Comercial",
    page_icon="⚙️",
    layout="centered"
)

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

supabase = init_supabase()

def calcular_cotizacion(precio_lista: float, cantidad: int, descuento_pct: float, incluir_igv: bool):
    precio_con_desc = precio_lista * (1 - (descuento_pct / 100.0))
    precio_unitario_final = precio_con_desc * 1.18 if incluir_igv else precio_con_desc
    total = precio_unitario_final * cantidad
    return round(precio_unitario_final, 2), round(total, 2)

st.title("⚙️ Cotizador de Productos")
st.caption("Consulta de precios y stock en tiempo real")

with st.container(border=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        codigo_busqueda = st.text_input("Código del producto", placeholder="Ej: 6203-2Z").strip().upper()
    with col2:
        marca_busqueda = st.text_input("Marca (Opcional)", placeholder="Ej: SKF").strip().upper()

    col3, col4, col5 = st.columns([1, 1, 1])
    with col3:
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
    with col4:
        descuento = st.number_input("Dscto (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0)
    with col5:
        st.write("")
        st.write("")
        con_igv = st.checkbox("Incluir IGV (18%)", value=True)

    buscar_btn = st.button("🔍 Buscar y Cotizar", type="primary", use_container_width=True)

if buscar_btn:
    if len(codigo_busqueda) < 2:
        st.warning("⚠️ Ingresa al menos 2 caracteres del código.")
    else:
        with st.spinner("Buscando..."):
            try:
                query = supabase.table("productos_cotizador").select("*").ilike("codigo", f"%{codigo_busqueda}%")
                if marca_busqueda:
                    query = query.ilike("marca", f"%{marca_busqueda}%")
                
                datos = query.limit(30).execute().data

                if not datos:
                    st.error("❌ No se encontraron productos con ese criterio.")
                else:
                    st.success(f"✅ Se encontraron {len(datos)} coincidencia(s):")
                    for item in datos:
                        p_unit, p_total = calcular_cotizacion(float(item["precio_lista"]), cantidad, descuento, con_igv)
                        stock = float(item["stock_fisico"])
                        color_stock = "🟢" if stock >= cantidad else ("🟡" if stock > 0 else "🔴")

                        with st.container(border=True):
                            c_info, c_precio = st.columns([2, 1])
                            with c_info:
                                st.markdown(f"### `{item['codigo']}` — **{item['marca']}**")
                                st.write(item["descripcion"])
                                st.markdown(f"{color_stock} **Stock:** `{stock:,.0f}` {item['und_medida']}")
                            with c_precio:
                                st.metric(label="Precio Unit.", value=f"S/ {p_unit:,.2f}")
                                if cantidad > 1:
                                    st.metric(label=f"Total ({cantidad} und.)", value=f"S/ {p_total:,.2f}")
            except Exception as e:
                st.error(f"Error de consulta: {e}")