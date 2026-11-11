import html
from typing import Any
from markupsafe import Markup
from sqladmin import ModelView
from sqladmin.filters import AllUniqueStringValuesFilter, ForeignKeyFilter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.admin.constants import (
    DEFAULT_MESSAGE_COUNT,
    DEFAULT_PAGE_SIZE,
    MESSAGES_TABLE_MAX_HEIGHT_PX,
    MESSAGES_TYPE_COLUMN_WIDTH_PX,
    PAGE_SIZE_OPTIONS,
    TEXT_PREVIEW_LIMIT,
    ZERO_MESSAGE_THRESHOLD,
)
from app.models.dialog import Dialog, DMessage


def format_total_messages(model: Dialog, attribute: Any) -> Markup | int:
    """
    Retorna el total de mensajes como enlace a su listado filtrado si es
    mayor a cero, o el valor numérico simple en caso contrario.
    """
    total = len(model.messages) if model.messages else DEFAULT_MESSAGE_COUNT
    if total > ZERO_MESSAGE_THRESHOLD:
        target_url = f"/admin/d-message/list?dialog_id={model.id}"
        return Markup(
            f'<a href="{target_url}" '
            f'class="fw-bold text-primary text-decoration-underline" '
            f'title="Ver mensajes filtrados">'
            f'{total}'
            f'</a>'
        )
    return total


def format_messages_detail_table(model: Dialog, attribute: Any) -> Markup:
    """
    Renderiza una tabla embebida con desplazamiento vertical conteniendo los mensajes
    asociados ordenados por su identificador numérico de manera ascendente.
    """
    messages = sorted(model.messages, key=lambda msg: msg.id) if model.messages else []
    if not messages:
        return Markup('<span class="text-muted">Sin mensajes asociados</span>')

    rows_html = []
    for msg in messages:
        msg_type_str = str(msg.type.value if hasattr(msg.type, "value") else msg.type)
        badge_class = (
            "bg-primary"
            if msg_type_str == "USER"
            else "bg-success"
            if msg_type_str == "ASSISTANT"
            else "bg-secondary"
        )
        escaped_text = html.escape(msg.text or "")
        row = (
            f"<tr>"
            f'<td style="width: {MESSAGES_TYPE_COLUMN_WIDTH_PX}px; vertical-align: top;">'
            f'<span class="badge {badge_class} text-white">{msg_type_str}</span>'
            f"</td>"
            f'<td style="white-space: pre-wrap; word-break: break-word;">{escaped_text}</td>'
            f"</tr>"
        )
        rows_html.append(row)

    table_content = "".join(rows_html)
    return Markup(
        f'<div style="max-height: {MESSAGES_TABLE_MAX_HEIGHT_PX}px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 4px;">'
        f'<table class="table table-sm table-striped table-hover mb-0 w-100">'
        f'<thead class="table-light" style="position: sticky; top: 0; z-index: 1;">'
        f"<tr>"
        f'<th style="width: {MESSAGES_TYPE_COLUMN_WIDTH_PX}px;">Tipo</th>'
        f"<th>Contenido</th>"
        f"</tr>"
        f"</thead>"
        f"<tbody>{table_content}</tbody>"
        f"</table>"
        f"</div>"
    )


def format_dialog_duuid(model: Dialog, attribute: Any) -> Markup:
    """
    Formatea el UUID del diálogo como un enlace hacia su vista de detalle.
    """
    target_url = f"/admin/dialog/details/{model.id}"
    return Markup(
        f'<a href="{target_url}" '
        f'class="fw-bold text-primary text-decoration-underline" '
        f'title="Ver detalles del diálogo">'
        f'{model.duuid}'
        f'</a>'
    )


def format_message_text(model: DMessage, attribute: Any) -> str:
    """
    Trunca el contenido de texto en el listado para una visualización ordenada.
    """
    text_content = model.text or ""
    if len(text_content) > TEXT_PREVIEW_LIMIT:
        return f"{text_content[:TEXT_PREVIEW_LIMIT]}..."
    return text_content


class BaseAdmin(ModelView):
    """
    Clase base para vistas administrativas con permisos restringidos:
    - Edición deshabilitada (los registros son inmutables).
    - Borrado deshabilitado en listados y habilitado exclusivamente
      desde la vista de detalle con confirmación modal.
    - Icono de detalle (ojo) oculto en los listados.
    """
    can_edit = False
    can_delete = True

    async def check_can_view_details(self, request: Request, model: Any) -> bool:
        # En la vista de listado se oculta el icono de ver detalles (ojo)
        if request.url.path.endswith("/list"):
            return False
        return self.can_view_details

    async def check_can_delete(self, request: Request, model: Any) -> bool:
        # En la vista de listado se deshabilita la opción de eliminar por fila
        if request.url.path.endswith("/list"):
            return False

        # Si la petición de borrado proviene de un listado, se deniega
        referer = request.headers.get("referer", "")
        if referer and "/list" in referer and "/details/" not in referer:
            return False

        return self.can_delete

    def _can_delete_any(self, request: Request) -> bool:
        # Oculta la opción y menú de borrado masivo en el listado
        if request.url.path.endswith("/list"):
            return False
        return self.can_delete


class DialogAdmin(BaseAdmin, model=Dialog):
    name = "Diálogo"
    name_plural = "Diálogos"
    icon = "fa-solid fa-comments"

    # Creación deshabilitada para diálogos
    can_create = False

    page_size = DEFAULT_PAGE_SIZE
    page_size_options = PAGE_SIZE_OPTIONS

    # Orden predeterminado al ingresar: fecha de creación descendente
    column_default_sort = [(Dialog.created_date, True)]

    column_list = [
        Dialog.id,
        Dialog.duuid,
        "total_messages",
        Dialog.created_date,
        Dialog.updated_date,
    ]

    column_details_list = [
        Dialog.id,
        Dialog.duuid,
        "total_messages",
        Dialog.created_date,
        Dialog.updated_date,
        "messages_table",
    ]

    # Columna ID no es ordenable
    column_sortable_list = [
        "total_messages",
        Dialog.created_date,
        Dialog.updated_date,
    ]

    column_searchable_list = [
        Dialog.duuid,
    ]

    column_labels = {
        Dialog.id: "ID",
        Dialog.duuid: "UUID",
        "total_messages": "Total Mensajes",
        Dialog.created_date: "Creado",
        Dialog.updated_date: "Actualizado",
        "messages_table": "Mensajes Asociados",
    }

    column_formatters = {
        Dialog.duuid: format_dialog_duuid,
        "total_messages": format_total_messages,
    }

    column_formatters_detail = {
        "total_messages": format_total_messages,
        "messages_table": format_messages_detail_table,
    }

    def list_query(self, request: Request) -> select:
        return select(Dialog).options(selectinload(Dialog.messages))

    def details_query(self, request: Request) -> select:
        return super().details_query(request).options(selectinload(Dialog.messages))

    def sort_query(self, stmt: select, request: Request) -> select:
        sort_by = request.query_params.get("sortBy", None)
        sort_order = request.query_params.get("sort", "asc")

        # Ordenamiento personalizado por conteo de mensajes con desempate por ID descendente
        if sort_by == "total_messages":
            count_subq = (
                select(func.count(DMessage.id))
                .where(DMessage.dialog_id == Dialog.id)
                .scalar_subquery()
            )
            if sort_order == "desc":
                return stmt.order_by(count_subq.desc(), Dialog.id.desc())
            return stmt.order_by(count_subq.asc(), Dialog.id.desc())

        # La columna creado ordena por ID
        if sort_by == "created_date":
            if sort_order == "desc":
                return stmt.order_by(Dialog.id.desc())
            return stmt.order_by(Dialog.id.asc())

        return super().sort_query(stmt, request)


class DMessageAdmin(BaseAdmin, model=DMessage):
    name = "Mensaje de Diálogo"
    name_plural = "Mensajes de Diálogo"
    icon = "fa-solid fa-message"

    page_size = DEFAULT_PAGE_SIZE
    page_size_options = PAGE_SIZE_OPTIONS

    column_list = [
        DMessage.id,
        DMessage.dialog_id,
        DMessage.type,
        DMessage.model,
        DMessage.text,
        DMessage.created_date,
    ]

    column_details_list = [
        DMessage.id,
        DMessage.dialog_id,
        DMessage.type,
        DMessage.model,
        DMessage.text,
        DMessage.usage,
        DMessage.created_date,
    ]

    column_sortable_list = [
        DMessage.id,
        DMessage.dialog_id,
        DMessage.created_date,
    ]

    column_searchable_list = [
        DMessage.text,
        DMessage.model,
    ]

    column_filters = [
        ForeignKeyFilter(
            foreign_key=DMessage.dialog_id,
            foreign_display_field=Dialog.id,
            foreign_model=Dialog,
            title="Diálogo",
        ),
        AllUniqueStringValuesFilter(
            column=DMessage.type,
            title="Tipo de Mensaje",
        ),
    ]

    column_labels = {
        DMessage.id: "ID",
        DMessage.dialog_id: "ID Diálogo",
        DMessage.type: "Tipo",
        DMessage.model: "Modelo LLM",
        DMessage.text: "Contenido",
        DMessage.usage: "Uso y Tokens (JSON)",
        DMessage.created_date: "Creado",
    }

    column_formatters = {
        DMessage.text: format_message_text,
    }
