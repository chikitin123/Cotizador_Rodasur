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
st.caption("Optimizado para celular y campo")

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
    # 📌 CONTENEDOR SUPERIOR FIJO (Diseñado para abrir el teclado táctil directo en celular)
    with st.container(border=True):
        # 1. Barra de texto libre: al tocarla en el celular, el teclado se abre inmediatamente
        texto_busqueda = st.text_input("🔍 Escribe para buscar sugerencias", placeholder="Ej. 6203, SKF, Faja...", key="input_texto")

        # 2. Filtramos en tiempo real según lo que escriba en el celular
        sugerencias_filtradas = []
        opciones_map = {}
        
        if texto_busqueda and len(texto_busqueda.strip()) > 0:
            busqueda_lower = texto_busqueda.strip().lower()
            for item in productos_totales:
                txt_completo = f"{item['codigo']} — {item['marca']} ({item['descripcion'][:35]}...)"
                if (busqueda_lower in item['codigo'].lower() or 
                    busqueda_lower in item['marca'].lower() or 
                    busqueda_lower in item['descripcion'].lower()):
                    sugerencias_filtradas.append(txt_completo)
                    opciones_map[txt_completo] = item['codigo']
        else:
            # Si no ha escrito nada, mostramos los primeros 30 productos para referencia rápida
            for item in productos_totales[:30]:
                txt_completo = f"{item['codigo']} — {item['marca']} ({item['descripcion'][:35]}...)"
                sugerencias_filtradas.append(txt_completo)
                opciones_map[txt_completo] = item['codigo']

        # 3. Selector que muestra las sugerencias basadas en lo que escribió
        seleccion_usuario = st.selectbox(
            "📋 Selecciona el producto sugerido:",
            options=["-- Elige una opción de la lista --"] + sugerencias_filtradas,
            key="select_sugerencia"
        )

        col3, col4, col5 = st.columns([1, 1, 1])
        with col3:
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1, key="num_cant")
        with col4:
            descuento = st.number_input("Dscto (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0, key="num_desc")
        with col5:
            st.write("")
            st.write("")
            con_igv = st.checkbox("Incluir IGV (18%)", value=True, key="chk_igv")

        # 🚀 BOTÓN COTIZAR FIJO ARRIBA
        btn_cotizar = st.button("🚀 Cotizar Producto", type="primary", use_container_width=True)

    # 📌 ZONA DE RESULTADOS INFERIOR (Nunca borra la parte de arriba)
    if btn_cotizar:
        if seleccion_usuario == "-- Elige una opción de la lista --":
            st.warning("⚠️ Por favor busca y selecciona un producto de las sugerencias.")
        else:
            codigo_seleccionado = opciones_map[seleccion_usuario]
            producto_encontrado = next((p for p in productos_totales if p["codigo"] == codigo_seleccionado), None)

            if not producto_encontrado:
                st.error("❌ Producto no encontrado.")
            else:
                moneda = producto_encontrado.get("moneda", "S/")
                precio_raw = float(producto_encontrado.get("precio_lista", 0.0))
                p_unit, p_total = calcular_cotizacion(precio_raw, cantidad, descuento, con_igv)
                stock = float(producto_encontrado.get("stock_fisico", 0.0))
                color_stock = "🟢" if stock >= cantidad else ("🟡" if stock > 0 else "🔴")

                st.success("✅ ¡Cotización generada!")
                with st.container(border=True):
                    c_info, c_precio = st.columns([2, 1])
                    with c_info:
                        st.markdown(f"### `{producto_encontrado['codigo']}` — **{producto_encontrado['marca']}**")
                        st.write(producto_encontrado["descripcion"])
                        st.markdown(f"{color_stock} **Stock:** `{stock:,.0f}` {producto_encontrado.get('und_medida', 'PZA')}")
                    with c_precio:
                        st.metric(label=f"Precio Unit. ({moneda})", value=f"{moneda} {p_unit:,.2f}")
                        if cantidad > 1:
                            st.metric(label=f"Total ({cantidad} und.)", value=f"{moneda} {p_total:,.2f}")
    else:
        st.info("💡 **Cómo usar en celular:** Escribe unas letras arriba para filtrar las sugerencias, selecciónala abajo, pon la cantidad y presiona **Cotizar Producto**.")
