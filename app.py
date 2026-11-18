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
st.caption("Búsqueda rápida por Código y Marca")

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
    # 📌 CONTENEDOR SUPERIOR FIJO CON DOS BARRAS (CÓDIGO Y MARCA)
    with st.container(border=True):
        st.markdown("### 🔍 Filtros de Búsqueda")
        
        c_bus1, c_bus2 = st.columns(2)
        with c_bus1:
            filtro_codigo = st.text_input("Código", placeholder="Ej. 6203, 32013...", key="input_filtro_codigo")
        with c_bus2:
            filtro_marca = st.text_input("Marca", placeholder="Ej. SKF, KOYO...", key="input_filtro_marca")

        col3, col4, col5 = st.columns([1, 1, 1])
        with col3:
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1, key="cant_val")
        with col4:
            descuento = st.number_input("Dscto (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0, key="desc_val")
        with col5:
            st.write("")
            st.write("")
            con_igv = st.checkbox("Incluir IGV (18%)", value=True, key="igv_val")

        # 🚀 BOTÓN COTIZAR
        btn_cotizar = st.button("🚀 Cotizar Producto", type="primary", use_container_width=True)

    # 📌 ZONA DE RESULTADOS INFERIOR
    if btn_cotizar:
        c_bus_str = filtro_codigo.strip().lower()
        m_bus_str = filtro_marca.strip().lower()

        if not c_bus_str and not m_bus_str:
            st.warning("⚠️ Por favor escribe al menos un Código o una Marca para buscar.")
        else:
            # Filtramos los productos que cumplan con los criterios ingresados
            resultados_filtrados = []
            for p in productos_totales:
                cod_val = str(p.get("codigo", "")).lower()
                mar_val = str(p.get("marca", "")).lower()
                
                # Comprobación independiente o combinada
                coincide_cod = (c_bus_str in cod_val) if c_bus_str else True
                coincide_mar = (m_bus_str in mar_val) if m_bus_str else True

                if coincide_cod and coincide_mar:
                    resultados_filtrados.append(p)

            if not resultados_filtrados:
                st.warning("❌ No se encontró ningún producto con esos filtros.")
            else:
                st.success(f"✅ Se encontraron {len(resultados_filtrados)} coincidencia(s):")
                
                for item in resultados_filtrados:
                    moneda = item.get("moneda", "S/")
                    precio_raw = float(item.get("precio_lista", 0.0))
                    p_unit, p_total = calcular_cotizacion(precio_raw, cantidad, descuento, con_igv)
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
        st.info("💡 **Cómo usar:** Escribe el código (ej. `6203`) y/o la marca (ej. `SKF`) en las barras superiores, ajusta la cantidad y presiona **Cotizar Producto**. Las barras se quedarán fijas para tu siguiente consulta.")
