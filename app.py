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
st.caption("Búsqueda inteligente con autocompletado en tiempo real")

# 1. Obtenemos todos los productos activos de Supabase para alimentar el autocompletado
@st.cache_data(ttl=60) # Cache por 60 segundos para que vuele la app
def obtener_lista_productos():
    try:
        res = supabase.table("productos_cotizador").select("codigo, marca, descripcion").limit(2000).execute()
        return res.data if res.data else []
    except:
        return []

productos_totales = obtener_lista_productos()

if not productos_totales:
    st.error("⚠️ La base de datos está vacía o no se pudo conectar. Ejecuta tu script de subida de Excel.")
else:
    # Creamos opciones combinadas para el buscador (Código + Marca + Descripción)
    opciones_map = {f"{item['codigo']} — {item['marca']} ({item['descripcion'][:40]}...)": item['codigo'] for item in productos_totales}
    lista_opciones = list(opciones_map.keys())

    with st.container(border=True):
        # Buscador interactivo con autocompletado nativo
        seleccion_usuario = st.selectbox(
            "🔍 Buscar por Código o Marca (Escribe para filtrar)",
            options=["-- Selecciona o escribe un código --"] + lista_opciones,
            index=0
        )

        col3, col4, col5 = st.columns([1, 1, 1])
        with col3:
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
        with col4:
            descuento = st.number_input("Dscto (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0)
        with col5:
            st.write("")
            st.write("")
            con_igv = st.checkbox("Incluir IGV (18%)", value=True)

    # Si el usuario seleccionó un producto válido
    if seleccion_usuario and seleccion_usuario != "-- Selecciona o escribe un código --":
        # Extraemos el código exacto del diccionario
        codigo_a_buscar = opciones_map[seleccion_usuario]

        with st.spinner("Calculando cotización..."):
            try:
                # Consultamos el detalle completo del producto seleccionado
                respuesta = supabase.table("productos_cotizador").select("*").eq("codigo", codigo_a_buscar).execute()
                datos = respuesta.data

                if not datos:
                    st.warning("❌ No hay resultados para este producto.")
                else:
                    for item in datos:
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
            except Exception as e:
                st.error(f"❌ Error al consultar el producto: {e}")
    elif seleccion_usuario == "-- Selecciona o escribe un código --":
        st.info("💡 Comienza a escribir en la barra superior el código (ej. `6203`) o marca para filtrar al instante.")
