import streamlit as st
from supabase import create_client, Client

st.set_page_config(
    page_title="Cotizador Comercial - Rodasur",
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
st.caption("Búsqueda rápida optimizada para celulares")

# Obtenemos productos de Supabase con caché
@st.cache_data(ttl=60)
def obtener_lista_productos():
    try:
        res = supabase.table("productos_cotizador").select("codigo, marca, descripcion, stock_fisico, precio_lista, moneda, und_medida").limit(3000).execute()
        return res.data if res.data else []
    except:
        return []

productos_totales = obtener_lista_productos()

if not productos_totales:
    st.error("⚠️ La base de datos está vacía. Ejecuta tu script de subida de Excel.")
else:
    # 📌 CONTENEDOR FIJO SUPERIOR: Nunca desaparece para que puedan buscar las veces que quieran
    with st.container(border=True):
        busqueda = st.text_input("🔍 Escribe el Código o la Marca", placeholder="Ej. 6203, SKF, Faja...", key="input_busqueda")

        col3, col4, col5 = st.columns([1, 1, 1])
        with col3:
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1, key="input_cantidad")
        with col4:
            descuento = st.number_input("Dscto (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0, key="input_dscto")
        with col5:
            st.write("")
            st.write("")
            con_igv = st.checkbox("Incluir IGV (18%)", value=True, key="input_igv")

    # 📌 ZONA DE RESULTADOS DINÁMICA: Se actualiza abajo sin perder la barra de arriba
    if busqueda and len(busqueda.strip()) > 0:
        texto_buscado = busqueda.strip().lower()
        
        resultados_filtrados = []
        for p in productos_totales:
            codigo = str(p.get("codigo", "")).lower()
            marca = str(p.get("marca", "")).lower()
            desc = str(p.get("descripcion", "")).lower()
            
            if texto_buscado in codigo or texto_buscado in marca or texto_buscado in desc:
                resultados_filtrados.append(p)

        if not resultados_filtrados:
            st.warning("❌ No se encontró ningún producto con ese criterio.")
        else:
            st.info(f"Se encontraron {len(resultados_filtrados)} coincidencia(s):")
            
            for item in resultados_filtrados:
                moneda = item.get("moneda", "S/")
                precio_raw = item.get("precio_lista", 0.0)
                p_unit, p_total = calcular_cotizacion(float(precio_raw), cantidad, descuento, con_igv)
                stock = float(item.get("stock_fisico", 0.0))
                color_stock = "🟢" if stock >= cantidad else ("🟡" if stock > 0 else "🔴")

                with st.container(border=True):
                    c_info, c_precio = st.columns([2, 1])
                    with c_info:
                        st.markdown(f"### `{item['codigo']}` — **{item['marca']}**")
                        st.write(item["descripcion"])
                        st.markdown(f"{color_stock} **Stock:** `{stock:,.0f}` {item.get('und_medida', 'PZA')}")
                    with c_precio:
                        st.metric(label=f"Precio Unit. ({moneda})", value=f"{moneda} {p_unit:,.2f}")
                        if cantidad > 1:
                            st.metric(label=f"Total ({cantidad} und.)", value=f"{moneda} {p_total:,.2f}")
    else:
        st.info("💡 Escribe en la barra superior el código o la marca para cotizar al instante. La barra se quedará siempre lista para tu siguiente búsqueda.")
