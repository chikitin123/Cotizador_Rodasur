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
st.caption("Búsqueda y sugerencias unificadas para celular")

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
    # 📌 CONTENEDOR SUPERIOR UNIFICADO Y FIJO
    with st.container(border=True):
        st.markdown("### 🔍 Buscador Inteligente")
        
        # 1. Barra de texto libre (Activa el teclado del celular al instante)
        busqueda_texto = st.text_input("Escribe el Código, Marca o Descripción:", placeholder="Ej. 6203, SKF, Faja...", key="input_buscador_unificado")

        # 2. Filtrado dinámico de sugerencias basado en lo que escribe el usuario
        opciones_map = {}
        lista_sugerencias = ["-- Escribe arriba para ver sugerencias --"]

        if busqueda_texto and len(busqueda_texto.strip()) > 0:
            texto_lower = busqueda_texto.strip().lower()
            for item in productos_totales:
                etiqueta = f"{item['codigo']} — {item['marca']} ({item['descripcion'][:40]}...)"
                if (texto_lower in item['codigo'].lower() or 
                    texto_lower in item['marca'].lower() or 
                    texto_lower in item['descripcion'].lower()):
                    opciones_map[etiqueta] = item['codigo']
                    lista_sugerencias.append(etiqueta)

        # 3. Selector que muestra las sugerencias encontradas al vuelo
        producto_seleccionado_label = st.selectbox(
            "📋 Selecciona de la lista de resultados:",
            options=lista_sugerencias,
            key="select_sugerencias_vuelo"
        )

        col3, col4, col5 = st.columns([1, 1, 1])
        with col3:
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1, key="cant_val")
        with col4:
            descuento = st.number_input("Dscto (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0, key="desc_val")
        with col5:
            st.write("")
            st.write("")
            con_igv = st.checkbox("Incluir IGV (18%)", value=True, key="igv_val")

        # 🚀 BOTÓN COTIZAR FIJO
        btn_cotizar = st.button("🚀 Cotizar Producto", type="primary", use_container_width=True)

    # 📌 ZONA DE RESULTADOS INFERIOR
    if btn_cotizar:
        if producto_seleccionado_label == "-- Escribe arriba para ver sugerencias --" or producto_seleccionado_label not in opciones_map:
            st.warning("⚠️ Por favor escribe en la barra, busca y selecciona un producto válido de las sugerencias.")
        else:
            codigo_real = opciones_map[producto_seleccionado_label]
            producto_encontrado = next((p for p in productos_totales if p["codigo"] == codigo_real), None)

            if not producto_encontrado:
                st.error("❌ Producto no encontrado.")
            else:
                moneda = producto_encontrado.get("moneda", "S/")
                precio_raw = float(producto_encontrado.get("precio_lista", 0.0))
                p_unit, p_total = calcular_cotizacion(precio_raw, cantidad, descuento, con_igv)
                stock = float(producto_encontrado.get("stock_fisico", 0.0))
                color_stock = "🟢" if stock >= cantidad else ("🟡" if stock > 0 else "🔴")

                st.success("✅ ¡Cotización generada con éxito!")
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
        st.info("💡 **Uso rápido en campo:** Toca la barra de texto (se abrirá el teclado), escribe el código o marca, selecciona la sugerencia abajo, ajusta la cantidad y presiona **Cotizar Producto**.")
