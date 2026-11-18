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
        res = supabase.table("productos_cotizador").select("codigo, marca, descripcion, stock_fisico, precio_lista, moneda, und_medida").limit(2000).execute()
        return res.data if res.data else []
    except:
        return []

productos_totales = obtener_lista_productos()

if not productos_totales:
    st.error("⚠️ La base de datos está vacía. Ejecuta tu script de subida de Excel.")
else:
    with st.container(border=True):
        # Usamos text_input para que en el celular aparezca el teclado de inmediato al hacer click
        busqueda = st.text_input("🔍 Escribe el Código o la Marca", placeholder="Ej. 6203, SKF, KOYO...")

        col3, col4, col5 = st.columns([1, 1, 1])
        with col3:
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
        with col4:
            descuento = st.number_input("Dscto (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0)
        with col5:
            st.write("")
            st.write("")
            con_igv = st.checkbox("Incluir IGV (18%)", value=True)

    if busqueda and len(busqueda.strip()) > 0:
        texto_filtro = busqueda.strip().upper()
        
        # Filtramos los productos que coincidan con el código o la marca en tiempo real
        resultados_filtrados = [
            p for p in productos_totales 
            if texto_filtro in p["codigo"].upper() or texto_filtro in p["marca"].upper() or texto_filtro in p["descripcion"].upper()
        ]

        if not resultados_filtrados:
            st.warning("❌ No se encontró ningún producto con ese criterio.")
        else:
            st.info(f"Se encontraron {len(resultados_filtrados)} coincidencia(s):")
            
            for item in resultados_filtrados:
                moneda = item.get("moneda", "S/")
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
                        st.metric(label=f"Precio Unit. ({moneda})", value=f"{moneda} {p_unit:,.2f}")
                        if cantidad > 1:
                            st.metric(label=f"Total ({cantidad} und.)", value=f"{moneda} {p_total:,.2f}")
    else:
        st.info("💡 Escribe parte del código o la marca arriba para buscar al instante desde el celular.")
