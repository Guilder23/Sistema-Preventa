from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from collections import defaultdict
from decimal import Decimal


@login_required
def dashboard(request):
    from apps.clientes.models import Cliente
    from apps.pedidos.models import DetallePedido, DevolucionItem, DevolucionPedido, Pedido
    from apps.productos.models import MovimientoInventario, Producto

    user = request.user
    perfil = getattr(user, "perfil", None)

    # Productos: todos visibles
    total_productos = Producto.objects.filter(activo=True).count()
    costo_inventario_total = sum(
        (
            (producto.stock_unidades or 0) * (producto.precio_compra_unidad or Decimal("0.00"))
            for producto in Producto.objects.filter(activo=True).only("stock_unidades", "precio_compra_unidad")
        ),
        Decimal("0.00"),
    )
    total_usuarios = User.objects.filter(is_active=True).count()

    movimientos_entrada_qs = MovimientoInventario.objects.filter(tipo=MovimientoInventario.TIPO_ENTRADA)
    movimientos_salida_qs = MovimientoInventario.objects.filter(tipo=MovimientoInventario.TIPO_SALIDA)
    total_unidades_ingresadas = movimientos_entrada_qs.aggregate(total=Sum("cantidad")).get("total") or 0
    valor_compra_ingresado_total = movimientos_entrada_qs.aggregate(total=Sum("valor_compra_total")).get("total") or Decimal("0.00")
    total_unidades_retiradas = movimientos_salida_qs.aggregate(total=Sum("cantidad")).get("total") or 0

    # Clientes: admin ve todos; preventista solo los suyos
    clientes_qs = Cliente.objects.filter(activo=True)
    if not user.is_superuser and perfil and perfil.rol == "preventista":
        clientes_qs = clientes_qs.filter(creado_por=user)
    total_clientes = clientes_qs.count()

    # Pedidos: admin ve todos; preventista solo los suyos
    pedidos_qs = Pedido.objects.all()
    if not user.is_superuser and perfil and perfil.rol == "preventista":
        pedidos_qs = pedidos_qs.filter(preventista=user)
    total_pedidos = pedidos_qs.count()

    hoy = timezone.localdate()
    pedidos_hoy_qs = pedidos_qs.filter(fecha__date=hoy)
    pedidos_hoy = pedidos_hoy_qs.count()
    pendientes_hoy = pedidos_hoy_qs.filter(estado=Pedido.ESTADO_PENDIENTE).count()
    anulados_hoy = pedidos_hoy_qs.filter(estado=Pedido.ESTADO_ANULADO).count()
    no_entregados_hoy = pedidos_hoy_qs.filter(estado=Pedido.ESTADO_NO_ENTREGADO).count()

    vendidos_hoy_qs = pedidos_qs.filter(
        estado=Pedido.ESTADO_VENDIDO,
        fecha_vendido__date=hoy,
    )
    vendidos_hoy = vendidos_hoy_qs.count()
    monto_vendido_hoy = vendidos_hoy_qs.aggregate(total=Sum("total")).get("total") or 0

    total_vendidos = pedidos_qs.filter(estado=Pedido.ESTADO_VENDIDO).count()
    total_pendientes = pedidos_qs.filter(estado=Pedido.ESTADO_PENDIENTE).count()
    total_anulados = pedidos_qs.filter(estado=Pedido.ESTADO_ANULADO).count()
    total_no_entregados = pedidos_qs.filter(estado=Pedido.ESTADO_NO_ENTREGADO).count()
    total_monto = pedidos_qs.aggregate(total=Sum("total")).get("total") or 0

    pedido_ids = list(pedidos_qs.values_list("id", flat=True))
    monto_devuelto_por_pedido = defaultdict(lambda: Decimal("0.00"))
    und_devueltas_por_pedido = defaultdict(int)
    devolucion_reciente_por_pedido = {}
    costo_vendido_total = Decimal("0.00")
    total_bruto_vendido = Decimal("0.00")

    if pedido_ids:
        devolucion_items = DevolucionItem.objects.filter(
            devolucion__pedido_id__in=pedido_ids,
            detalle_pedido__isnull=False,
        ).select_related("detalle_pedido__producto", "devolucion")

        for it in devolucion_items:
            precio = it.detalle_pedido.precio_unitario if it.detalle_pedido else Decimal("0.00")
            monto_devuelto_por_pedido[it.devolucion.pedido_id] += (precio or Decimal("0.00")) * Decimal(int(it.cantidad_devuelta or 0))
            if it.detalle_pedido_id:
                und_devueltas_por_pedido[it.detalle_pedido_id] += int(it.cantidad_devuelta or 0)

        devoluciones = (
            DevolucionPedido.objects.filter(pedido_id__in=pedido_ids)
            .select_related("repartidor")
            .order_by("pedido_id", "-fecha_creacion")
        )
        for d in devoluciones:
            if d.pedido_id not in devolucion_reciente_por_pedido:
                devolucion_reciente_por_pedido[d.pedido_id] = d

        pedidos_vendidos_qs = pedidos_qs.filter(estado=Pedido.ESTADO_VENDIDO)
        total_bruto_vendido = pedidos_vendidos_qs.aggregate(total=Sum("total")).get("total") or Decimal("0.00")

        detalles_vendidos = (
            DetallePedido.objects.filter(pedido_id__in=pedidos_vendidos_qs.values_list("id", flat=True))
            .select_related("pedido", "producto")
        )
        for detalle in detalles_vendidos:
            devueltas = int(und_devueltas_por_pedido.get(detalle.id, 0))
            cantidad_vendida = max(int(detalle.cantidad or 0) - devueltas, 0)
            costo_vendido_total += Decimal(cantidad_vendida) * (detalle.producto.precio_compra_unidad or Decimal("0.00"))

    total_devuelto_monto = sum(monto_devuelto_por_pedido.values(), Decimal("0.00"))
    total_real_vendido = total_bruto_vendido - total_devuelto_monto
    ganancia_real_total = total_real_vendido - costo_vendido_total

    vendidos_hoy_ids = list(vendidos_hoy_qs.values_list("id", flat=True))
    devuelto_hoy_en_vendidos = sum((monto_devuelto_por_pedido.get(pid, Decimal("0.00")) for pid in vendidos_hoy_ids), Decimal("0.00"))
    ventas_netas_hoy = (monto_vendido_hoy or Decimal("0.00")) - devuelto_hoy_en_vendidos

    costo_vendido_hoy = Decimal("0.00")
    if vendidos_hoy_ids:
        detalles_hoy = DetallePedido.objects.filter(pedido_id__in=vendidos_hoy_ids).select_related("pedido", "producto")
        for detalle in detalles_hoy:
            devueltas = int(und_devueltas_por_pedido.get(detalle.id, 0))
            cantidad_vendida = max(int(detalle.cantidad or 0) - devueltas, 0)
            costo_vendido_hoy += Decimal(cantidad_vendida) * (detalle.producto.precio_compra_unidad or Decimal("0.00"))

    ganancia_real_hoy = ventas_netas_hoy - costo_vendido_hoy

    devoluciones_qs = DevolucionPedido.objects.filter(pedido_id__in=pedido_ids)
    entregas_parciales_total = devoluciones_qs.filter(tipo=DevolucionPedido.TIPO_PARCIAL).values("pedido_id").distinct().count()
    entregas_parciales_hoy = devoluciones_qs.filter(tipo=DevolucionPedido.TIPO_PARCIAL, fecha_creacion__date=hoy).values("pedido_id").distinct().count()

    pedidos_recientes = list(
        pedidos_qs.select_related("cliente", "cliente__creado_por", "preventista", "registrado_por")
        .order_by("-fecha")[:10]
    )

    for p in pedidos_recientes:
        p.total_real = (p.total or Decimal("0.00")) - monto_devuelto_por_pedido.get(p.id, Decimal("0.00"))
        p.devueltos_unidades = und_devueltas_por_pedido.get(p.id, 0)

        creado_por_cliente = getattr(p.cliente, "creado_por", None)
        p.cliente_registrado_por = (
            (creado_por_cliente.get_full_name() or creado_por_cliente.username)
            if creado_por_cliente
            else "-"
        )

        registrador = getattr(p, "registrado_por", None)
        p.pedido_registrado_por = (
            (registrador.get_full_name() or registrador.username)
            if registrador
            else (p.preventista.get_full_name() or p.preventista.username)
        )

        devol = devolucion_reciente_por_pedido.get(p.id)
        p.repartidor_nombre = (
            (devol.repartidor.get_full_name() or devol.repartidor.username)
            if devol and devol.repartidor
            else "-"
        )

        if p.estado == Pedido.ESTADO_NO_ENTREGADO:
            p.estado_entrega = "No entregado"
        elif p.estado == Pedido.ESTADO_VENDIDO and devol and devol.tipo == DevolucionPedido.TIPO_PARCIAL:
            p.estado_entrega = "Entregado parcial"
        elif p.estado == Pedido.ESTADO_VENDIDO:
            p.estado_entrega = "Entregado completo"
        elif p.estado == Pedido.ESTADO_PENDIENTE:
            p.estado_entrega = "Pendiente"
        else:
            p.estado_entrega = "-"

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "total_productos": total_productos,
            "total_clientes": total_clientes,
            "total_usuarios": total_usuarios,
            "total_pedidos": total_pedidos,
            "total_vendidos": total_vendidos,
            "total_pendientes": total_pendientes,
            "total_anulados": total_anulados,
            "total_monto": total_monto,
            "costo_inventario_total": costo_inventario_total,
            "total_unidades_ingresadas": total_unidades_ingresadas,
            "valor_compra_ingresado_total": valor_compra_ingresado_total,
            "total_unidades_retiradas": total_unidades_retiradas,
            "pedidos_hoy": pedidos_hoy,
            "pendientes_hoy": pendientes_hoy,
            "anulados_hoy": anulados_hoy,
            "no_entregados_hoy": no_entregados_hoy,
            "vendidos_hoy": vendidos_hoy,
            "monto_vendido_hoy": monto_vendido_hoy,
            "ventas_netas_hoy": ventas_netas_hoy,
            "ganancia_real_hoy": ganancia_real_hoy,
            "total_bruto_vendido": total_bruto_vendido,
            "total_devuelto_monto": total_devuelto_monto,
            "total_real_vendido": total_real_vendido,
            "ganancia_real_total": ganancia_real_total,
            "total_no_entregados": total_no_entregados,
            "entregas_parciales_total": entregas_parciales_total,
            "entregas_parciales_hoy": entregas_parciales_hoy,
            "pedidos_recientes": pedidos_recientes,
        },
    )


@login_required
def ayuda(request):
    rol = ""
    if request.user.is_superuser:
        rol = "administrador"
    elif hasattr(request.user, "perfil"):
        rol = request.user.perfil.rol or "preventista"
    
    # Contenido de ayuda por rol
    ayuda_contenido = {
        "administrador": {
            "titulo": "Guía del Administrador",
            "descripcion": "Panel completo de control del sistema. Acceso a todas las secciones y decisiones clave.",
            "secciones": [
                {
                    "titulo": "Dashboard - Panel de Control",
                    "icono": "fa-gauge",
                    "contenido": [
                        "Visualiza métricas clave del negocio en tiempo real",
                        "Monta total de ventas, clientes activos y productos disponibles",
                        "Seguimiento del inventario: unidades agregadas, valor de compras, unidades retiradas",
                        "Nuevos ordenes hoy, estado de entregas (pendientes, vendidos, no entregados)"
                    ],
                    "pasos": [
                        "Accede a Dashboard desde el menú principal",
                        "Revisa las tarjetas KPI (Ventas, Ganancias, Inventario)",
                        "Haz clic en cualquier tarjeta para ver detalles detallados"
                    ]
                },
                {
                    "titulo": "Gestión de Clientes",
                    "icono": "fa-users",
                    "contenido": [
                        "Crea, edita y gestiona toda la base de clientes",
                        "Registra ubicación del cliente en el mapa (opcional)",
                        "Marca clientes como activos o inactivos",
                        "Asigna clientes específicos a preventistas"
                    ],
                    "pasos": [
                        "Ve a Clientes en el menú PREVENTA",
                        "Haz clic en 'Nuevo Cliente' para agregar",
                        "Completa: nombre, teléfono, correo, tipo de negocio",
                        "Usa 'Ver Mapa' para ubicar la tienda en el mapa"
                    ]
                },
                {
                    "titulo": "Administración de Productos",
                    "icono": "fa-cube",
                    "contenido": [
                        "Solo admin puede crear, editar y bloquear productos",
                        "Define código único, nombre, descripción y foto",
                        "Establece precios de compra y venta (unidad y caja)",
                        "Gestiona inventario mediante el modal de ajustes"
                    ],
                    "pasos": [
                        "Ve a Productos en el menú PREVENTA",
                        "Para crear: haz clic en 'Nuevo Producto'",
                        "Completa todos los campos requeridos",
                        "Para ajustar stock: haz clic en el ícono de cajas",
                        "Registra entrada/salida con motivo y cantidad"
                    ]
                },
                {
                    "titulo": "Gestión de Pedidos",
                    "icono": "fa-shopping-bag",
                    "contenido": [
                        "Crea y controla todos los pedidos del sistema",
                        "Visualiza estado: pendiente, vendido, no entregado, anulado",
                        "Consulta historial completo de transacciones",
                        "Genera reportes PDF de cada pedido"
                    ],
                    "pasos": [
                        "Ve a Pedidos en el menú PREVENTA",
                        "Haz clic en 'Nuevo Pedido'",
                        "Selecciona cliente y agrega productos",
                        "Marca como vendido una vez completado",
                        "Imprime PDF si es necesario"
                    ]
                },
                {
                    "titulo": "Devoluciones",
                    "icono": "fa-undo",
                    "contenido": [
                        "Registra y gestiona devoluciones de productos",
                        "Asocia devoluciones a pedidos específicos",
                        "Controla qué productos fueron devueltos y cantidades",
                        "Actualiza inmediatamente el inventario"
                    ],
                    "pasos": [
                        "Ve a Devoluciones en el menú PREVENTA",
                        "Selecciona el pedido que tiene devoluciones",
                        "Agrega cada producto devuelto y cantidad",
                        "Asigna repartidor responsable",
                        "Guarda para actualizar inventario automáticamente"
                    ]
                },
                {
                    "titulo": "Reportes y Análisis",
                    "icono": "fa-chart-bar",
                    "contenido": [
                        "Accede a reportes detallados de ventas",
                        "Analiza rendimiento por cliente, producto o período",
                        "Exporta datos para análisis externo",
                        "Filtra por fechas y criterios específicos"
                    ],
                    "pasos": [
                        "Ve a Reportes en el menú PREVENTA",
                        "Selecciona el tipo de reporte deseado",
                        "Aplica filtros (fechas, clientes, productos)",
                        "Descarga o visualiza resultados"
                    ]
                },
                {
                    "titulo": "Gestión de Usuarios",
                    "icono": "fa-person-badge",
                    "contenido": [
                        "Crea y administra cuentas de supervisor, repartidor y preventista",
                        "Asigna roles y permisos específicos",
                        "Activa o desactiva usuarios",
                        "Controla acceso al sistema"
                    ],
                    "pasos": [
                        "Ve a Usuarios en el menú SISTEMA",
                        "Haz clic en 'Nuevo Usuario'",
                        "Asigna nombre, correo, teléfono y rol",
                        "El usuario recibirá instrucciones por correo",
                        "Edita después si necesitas cambiar rol"
                    ]
                }
            ]
        },
        "supervisor": {
            "titulo": "Guía del Supervisor",
            "descripcion": "Supervisa las operaciones de preventistas y repartidores bajo tu área.",
            "secciones": [
                {
                    "titulo": "Funciones del Supervisor",
                    "icono": "fa-person-hiking",
                    "contenido": [
                        "Supervisa preventistas y repartidores de tu zona",
                        "Revisa todos los pedidos de tu equipo",
                        "Accede a reportes de desempeño",
                        "Valida transacciones antes de finalizar"
                    ],
                    "pasos": [
                        "Revisa el Dashboard para ver métricas de tu equipo",
                        "Ve a Pedidos para supervisar transacciones",
                        "Haz clic en 'Ver' para detalles de cada pedido",
                        "Valida estados y descarga reportes"
                    ]
                },
                {
                    "titulo": "Gestión de Clientes",
                    "icono": "fa-users",
                    "contenido": [
                        "Visualiza clientes asignados a tu zona",
                        "Puedes crear clientes nuevos en tu área",
                        "Revisa información de contacto y ubicación",
                        "Actualiza datos si es necesario"
                    ],
                    "pasos": [
                        "Ve a Clientes en el menú PREVENTA",
                        "Visualiza lista de clientes de tu supervisión",
                        "Usa el mapa para ver ubicaciones",
                        "Actualiza información según sea necesario"
                    ]
                },
                {
                    "titulo": "Consulta de Productos",
                    "icono": "fa-cube",
                    "contenido": [
                        "Visualiza catálogo completo de productos",
                        "Revisa precios de compra y venta",
                        "Verifica niveles de inventario",
                        "Consulta histórico de movimientos"
                    ],
                    "pasos": [
                        "Ve a Productos en el menú PREVENTA",
                        "Visualiza el catálogo completo",
                        "Haz clic en 'Ver Inventario' para detalles",
                        "Revisa historial de entradas/salidas"
                    ]
                },
                {
                    "titulo": "Seguimiento de Pedidos",
                    "icono": "fa-shopping-bag",
                    "contenido": [
                        "Consulta todos los pedidos de tu zona",
                        "Filtra por estado, cliente o preventista",
                        "Revisa detalles y montos",
                        "Descarga reportes en PDF"
                    ],
                    "pasos": [
                        "Ve a Pedidos en el menú PREVENTA",
                        "Aplica filtros para ver tu zona",
                        "Haz clic en un pedido para detalles",
                        "Usa 'Imprimir PDF' para reportes"
                    ]
                }
            ]
        },
        "repartidor": {
            "titulo": "Guía del Repartidor",
            "descripcion": "Tu función es entregar pedidos y registrar devoluciones.",
            "secciones": [
                {
                    "titulo": "Tu Rol como Repartidor",
                    "icono": "fa-truck",
                    "contenido": [
                        "Entregas pedidos a clientes finales",
                        "Registras devoluciones de productos defectuosos",
                        "Recolectas pagos (si aplica)",
                        "Reportas estado de entregas"
                    ],
                    "pasos": [
                        "Revisa Dashboard para ver resumen",
                        "Ve a Pedidos para consultar tus entregas",
                        "Toma nota de la información del cliente",
                        "Entrega el pedido",
                        "Si hay devoluciones, regresa al sistema"
                    ]
                },
                {
                    "titulo": "Consulta de Pedidos",
                    "icono": "fa-shopping-bag",
                    "contenido": [
                        "Visualiza todos los pedidos asignados para entrega",
                        "Revisa ubicación del cliente en el mapa",
                        "Consulta productos y cantidades",
                        "Verifica dirección y contacto"
                    ],
                    "pasos": [
                        "Ve a Pedidos en el menú superior",
                        "Haz clic en un pedido para ver detalles",
                        "Usa 'Ver Mapa' para ubicación del cliente",
                        "Ten a mano teléfono del cliente"
                    ]
                },
                {
                    "titulo": "Registrar Devoluciones",
                    "icono": "fa-undo",
                    "contenido": [
                        "Si el cliente devuelve productos, regístralo en el sistema",
                        "Especifica qué productos se devuelven",
                        "Nota problemas (daño, color, etc.)",
                        "Confirma para actualizar inventario"
                    ],
                    "pasos": [
                        "Ve a Devoluciones en el menú superior",
                        "Selecciona el pedido con devoluciones",
                        "Agrega cada producto devuelto",
                        "Escribe motivo de devolución",
                        "Presiona 'Guardar Devolución'"
                    ]
                },
                {
                    "titulo": "Ver Ubicación en Mapa",
                    "icono": "fa-map",
                    "contenido": [
                        "Consulta la ubicación del cliente en el mapa",
                        "Planifica tu ruta de entregas",
                        "Evita errores de dirección",
                        "Calcula tiempo de desplazamiento"
                    ],
                    "pasos": [
                        "Ve al Mapa en el menú superior",
                        "Busca el cliente en el mapa",
                        "Visualiza dirección exacta",
                        "Usa GPS o navegador externo si necesitas"
                    ]
                }
            ]
        },
        "preventista": {
            "titulo": "Guía del Preventista",
            "descripcion": "Tu función es crear pedidos y gestionar clientes de tu zona.",
            "secciones": [
                {
                    "titulo": "Tu Rol como Preventista",
                    "icono": "fa-person-biking",
                    "contenido": [
                        "Eres vendedor en tu zona de cobertura",
                        "Creas pedidos para tus clientes",
                        "Registras nuevos clientes",
                        "Consultas productos disponibles y precios",
                        "Ves tus comisiones y desempeño"
                    ],
                    "pasos": [
                        "Ingresa a tu Dashboard personal",
                        "Revisa clientes asignados a tu zona",
                        "Consulta catálogo de productos",
                        "Crea pedidos para tus clientes",
                        "Revisa tus números y comisiones"
                    ]
                },
                {
                    "titulo": "Gestión de Clientes",
                    "icono": "fa-users",
                    "contenido": [
                        "Administra clientes de tu zona de cobertura",
                        "Registra nuevos clientes con ubicación",
                        "Actualiza información de contacto",
                        "Consulta historial de compras de cada cliente",
                        "Ve ubicación en mapa"
                    ],
                    "pasos": [
                        "Ve a Clientes en el menú PREVENTA",
                        "Visualiza tus clientes ",
                        "Para nuevo: haz clic en 'Nuevo Cliente'",
                        "Completa: nombre, teléfono, correo, ubicación",
                        "Usa 'Ver Mapa' para visualizar área de cobertura"
                    ]
                },
                {
                    "titulo": "Consulta de Productos",
                    "icono": "fa-cube",
                    "contenido": [
                        "Consulta catálogo completo de productos",
                        "Revisa precios de venta (lo que cobras al cliente)",
                        "Verifica disponibilidad y stock",
                        "Ver descripción y foto de cada producto"
                    ],
                    "pasos": [
                        "Ve a Productos en el menú PREVENTA",
                        "Revisa el catálogo en la tabla",
                        "Haz clic en un producto para ver detalles",
                        "Anota precios unitario y caja para tus clientes"
                    ]
                },
                {
                    "titulo": "Crear Pedidos",
                    "icono": "fa-shopping-bag",
                    "contenido": [
                        "Crea pedidos para tus clientes",
                        "Agrega múltiples productos en una orden",
                        "Define cantidad de unidades o cajas",
                        "El sistema calcula total automáticamente",
                        "Guarda pedido para transferencia a repartidor"
                    ],
                    "pasos": [
                        "Ve a Pedidos en el menú PREVENTA",
                        "Haz clic en 'Nuevo Pedido'",
                        "Selecciona el cliente de tu lista",
                        "Agrega productos con cantidades",
                        "Revisa total y haz clic en 'Guardar Pedido'",
                        "El repartidor entregará después"
                    ]
                },
                {
                    "titulo": "Ubicación del Cliente en Mapa",
                    "icono": "fa-map",
                    "contenido": [
                        "Visualiza la ubicación de cada cliente",
                        "Planifica tu ruta de ventas",
                        "Coordina con repartidor para entregas",
                        "Calcula distancias entre clientes"
                    ],
                    "pasos": [
                        "Ve a Mapa en el menú PREVENTA",
                        "Visualiza todos tus clientes en el mapa",
                        "Haz clic en un marcador para detalles",
                        "Planifica orden de visitas"
                    ]
                },
                {
                    "titulo": "Ver Tu Desempeño",
                    "icono": "fa-chart-line",
                    "contenido": [
                        "Consulta tus números en el Dashboard",
                        "Revisa total de pedidos creados",
                        "Ve monto vendido en el período",
                        "Compara con metas y comisiones",
                        "Descarga reportes de tu desempeño"
                    ],
                    "pasos": [
                        "Abre Dashboard desde el menú",
                        "Revisa las tarjetas KPI",
                        "Ve a Reportes para análisis detalladoss",
                        "Descarga reportes en PDF"
                    ]
                }
            ]
        }
    }

    # Conceptos importantes que aplican a todos
    conceptos = [
        {
            "titulo": "¿Qué es un PEDIDO?",
            "contenido": "Un pedido es una orden de compra que contiene uno o más productos con cantidades específicas. Puede estar en estado pendiente (creado), vendido (completado y pagado) o devuelto (cliente quiere cambiar productos).",
            "icono": "fa-file-invoice"
        },
        {
            "titulo": "¿Qué es una DEVOLUCIÓN?",
            "contenido": "Es cuando un cliente devuelve productos de un pedido ya vendido. Puede ser por defecto, cambio de color, mal despacho, etc. Se registra en el sistema para actualizar el inventario.",
            "icono": "fa-sync"
        },
        {
            "titulo": "¿Qué es el INVENTARIO?",
            "contenido": "Es el registro de todos los productos disponibles. Se actualiza cuando se agregan (compras) o se retiran (ventas, devoluciones). El valor de inventario = cantidad × precio de compra.",
            "icono": "fa-warehouse"
        },
        {
            "titulo": "¿Qué es una GANANCIA?",
            "contenido": "La ganancia es la diferencia entre el precio de venta y el precio de compra. Por ejemplo: compras a 10, vendes a 20, ganancias = 10 por unidad.",
            "icono": "fa-chart-pie"
        },
        {
            "titulo": "ESTADOS DE PEDIDO",
            "contenido": "Pendiente: no completado. Vendido: pagado y entregado. No Entregado: cliente rechazó. Anulado: se canceló la orden. Devuelto: cliente devolvió parte o todo.",
            "icono": "fa-list-check"
        },
        {
            "titulo": "¿QUÉ ES LA COMISIÓN?",
            "contenido": "Es el monto que gana un preventista por cada venta realizada. Se calcula como un porcentaje de la ganancia del pedido, no del total vendido.",
            "icono": "fa-coins"
        }
    ]

    # Información de soporte
    soporte = {
        "telefono": "68440201",
        "whatsapp": "68440201",
        "website": "appyaa.com",
        "email": "soporte@appyaa.com",
        "redes_sociales": [
            {"nombre": "Facebook", "icono": "fab fa-facebook-f", "enlace": "https://facebook.com/appyaa"},
            {"nombre": "TikTok", "icono": "fab fa-tiktok", "enlace": "https://tiktok.com/@appyaa"},
            {"nombre": "X (Twitter)", "icono": "fab fa-x-twitter", "enlace": "https://x.com/appyaa"},
            {"nombre": "WhatsApp", "icono": "fab fa-whatsapp", "enlace": "https://wa.me/+59168440201"}
        ]
    }

    contexto = {
        "rol": rol,
        "ayuda": ayuda_contenido.get(rol, ayuda_contenido["preventista"]),
        "conceptos": conceptos,
        "soporte": soporte,
        "roles_disponibles": list(ayuda_contenido.keys())
    }
    
    return render(request, "dashboard/ayuda.html", contexto)


@login_required
def configuracion(request):
    return render(request, "dashboard/configuracion.html")
