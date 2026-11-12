import html
import json
from typing import Any
from uuid import UUID
from markupsafe import Markup
from sqladmin import ModelView
from sqladmin.filters import AllUniqueStringValuesFilter, ForeignKeyFilter
from sqlalchemy import func, or_, select
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
from app.models.dialog import Dialog, DMessage, DMessageType


def format_total_messages(model: Dialog, attribute: Any) -> Markup | int:
    """
    Retorna el total de mensajes como enlace a su listado filtrado si es
    mayor a cero, o el valor numérico simple en caso contrario.
    """
    total = len(model.messages) if model.messages else DEFAULT_MESSAGE_COUNT
    if total > ZERO_MESSAGE_THRESHOLD:
        target_url = f"/admin/d-message/list?dialog_uuid={model.duuid}"
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
        msg_type_str = DMessageType.get_label(msg.type)
        badge_class = DMessageType.get_badge_class(msg.type)
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



def format_dialog_model(model: Dialog, attribute: Any) -> Markup:
    model_name = html.escape(model.model or "Ningún modelo")
    return Markup(
        f'<span class="badge rounded-pill bg-primary text-white" '
        f'style="font-size: 0.7rem;">{model_name}</span>'
    )

def format_dialog_duuid(model: Dialog, attribute: Any) -> Markup:
    """
    Formatea el UUID del diálogo como un enlace hacia su vista de detalle.
    """
    target_url = f"/admin/dialog/details/{model.duuid}"
    return Markup(
        f'<a href="{target_url}" '
        f'class="fw-bold text-primary text-decoration-underline" '
        f'title="Ver detalles del diálogo">'
        f'{model.duuid}'
        f'</a>'
    )


def format_message_text(model: DMessage, attribute: Any) -> str | Markup:
    """Trunca el contenido largo y permite expandir un único mensaje."""
    text_content = model.text or ""
    if len(text_content) <= TEXT_PREVIEW_LIMIT:
        return text_content

    preview = html.escape(text_content[:TEXT_PREVIEW_LIMIT]) + "..."
    full_text = html.escape(text_content)
    content_id = f"message-content-{model.id}"
    return Markup(
        '<div class="message-content">'
        f'<span class="message-content-preview">{preview}</span>'
        f'<div id="{content_id}" class="message-content-full" '
        'style="white-space: pre-wrap; word-break: break-word;" hidden>'
        f'{full_text}</div>'
        f'<button type="button" class="btn btn-link btn-sm p-0 message-content-toggle" '
        f'aria-controls="{content_id}" aria-expanded="false">Ver completo</button>'
        '</div>'
    )

def format_message_type(model: DMessage, attribute: Any) -> Markup:
    message_type = DMessageType.get_label(model.type)
    badge_class = DMessageType.get_badge_class(model.type)
    badge_content = html.escape(message_type)
    if message_type == DMessageType.ASSISTANT.label and model.model:
        model_name = html.escape(model.model, quote=True)
        return Markup(
            f'<span class="badge {badge_class} text-white" '
            f'title="Modelo LLM:<br><strong>{model_name}</strong>" '
            f'data-bs-toggle="tooltip" data-bs-html="true">{badge_content}</span>'
        )
    return Markup(f'<span class="badge {badge_class} text-white">{badge_content}</span>')

def format_message_dialog(model: DMessage, attribute: Any) -> Markup:
    """Enlaza al diálogo asociado usando su UUID público."""
    dialog_uuid = model.dialog.duuid
    target_url = f"/admin/dialog/details/{dialog_uuid}"
    return Markup(
        f'<a href="{target_url}" '
        f'class="fw-bold text-primary text-decoration-underline" '
        f'title="Ver detalles del diálogo">{dialog_uuid}</a>'
    )


class DialogUUIDFilter(ForeignKeyFilter):
    """Filtra mensajes por el UUID público del diálogo relacionado."""
    template = "sqladmin/filters/dialog_uuid_filter.html"

    async def lookups(self, request: Request, model: Any, run_query: Any) -> list[tuple[str, str]]:
        return [("__all", "Todos")] + [
            (str(duuid), str(duuid))
            for duuid, in await run_query(select(Dialog.duuid).distinct())
        ]

    async def get_filtered_query(self, query: select, value: Any, model: Any) -> select:
        if value in (None, "", "__all"):
            return query
        try:
            dialog_uuid = UUID(value)
        except (ValueError, TypeError):
            return query.filter(False)
        return query.join(Dialog, DMessage.dialog_id == Dialog.id).filter(
            Dialog.duuid == dialog_uuid
        )



class DMessageModelFilter(AllUniqueStringValuesFilter):
    """Filtro de modelos LLM con selección múltiple."""
    NO_MODEL_VALUE = "__no_model__"

    template = "sqladmin/filters/dmessage_model_filter.html"

    @staticmethod
    def parse_values(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            values = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
        if not isinstance(values, list):
            return []
        return [item for item in values if isinstance(item, str)]
    @classmethod
    def display_entries(cls, values: list[str]) -> list[tuple[str, str]]:
        return [
            (value, "Ningún modelo" if value == cls.NO_MODEL_VALUE else value)
            for value in values
        ]

    async def lookups(self, request: Request, model: Any, run_query: Any) -> list[tuple[str, str]]:
        model_lookups = [
            (value, value)
            for value, in await run_query(
                select(Dialog.model).where(Dialog.model.is_not(None)).distinct()
            )
            if value
        ]
        return [(self.NO_MODEL_VALUE, "Ningún modelo")] + model_lookups

    async def get_filtered_query(self, query: select, value: Any, model: Any) -> select:
        selected_values = self.parse_values(value)
        model_names = [
            model_name
            for model_name in selected_values
            if model_name != self.NO_MODEL_VALUE
        ]
        include_no_model = self.NO_MODEL_VALUE in selected_values
        if not model_names and not include_no_model:
            return query
        conditions = []
        if model_names:
            conditions.append(Dialog.model.in_(model_names))
        if include_no_model:
            conditions.append(Dialog.model.is_(None))
        dialog_ids = select(Dialog.id).where(or_(*conditions))
        return query.filter(DMessage.dialog_id.in_(dialog_ids))



class DialogModelFilter(DMessageModelFilter):
    """Aplica el filtro múltiple directamente a Dialog.model."""

    async def get_filtered_query(self, query: select, value: Any, model: Any) -> select:
        selected_values = self.parse_values(value)
        model_names = [
            model_name
            for model_name in selected_values
            if model_name != self.NO_MODEL_VALUE
        ]
        include_no_model = self.NO_MODEL_VALUE in selected_values
        if not model_names and not include_no_model:
            return query
        conditions = []
        if model_names:
            conditions.append(Dialog.model.in_(model_names))
        if include_no_model:
            conditions.append(Dialog.model.is_(None))
        return query.filter(or_(*conditions))

class DMessageTypeFilter(AllUniqueStringValuesFilter):
    """Devuelve las etiquetas y colores del enum para el filtro por tipo."""

    template = "sqladmin/filters/dmessage_type_filter.html"

    async def lookups(self, request: Request, model: Any, run_query: Any) -> list[tuple[str, str, str]]:
        return [
            (message_type.value, DMessageType.get_label(message_type), DMessageType.get_badge_class(message_type))
            for message_type in DMessageType
        ]
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
    list_template = "sqladmin/dialog_list.html"
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
        Dialog.model,
        "total_messages",
        Dialog.created_date,
        Dialog.updated_date,
    ]

    column_details_list = [
        Dialog.id,
        Dialog.duuid,
        Dialog.model,
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
    column_filters = [
        DialogModelFilter(
            column=Dialog.model,
            title="Modelo LLM",
            parameter_name="dialog_models",
        ),
    ]

    column_labels = {
        Dialog.id: "ID",
        Dialog.duuid: "UUID",
        Dialog.model: "Modelo LLM",
        "total_messages": "Total Mensajes",
        Dialog.created_date: "Creado",
        Dialog.updated_date: "Actualizado",
        "messages_table": "Mensajes Asociados",
    }

    column_formatters = {
        Dialog.duuid: format_dialog_duuid,
        Dialog.model: format_dialog_model,
        "total_messages": format_total_messages,
    }

    column_formatters_detail = {
        Dialog.model: format_dialog_model,
        "total_messages": format_total_messages,
        "messages_table": format_messages_detail_table,
    }

    async def list_context(self, request: Request) -> dict[str, Any]:
        filter_reset_url = request.url
        for dialog_filter in self.get_filters():
            filter_reset_url = filter_reset_url.remove_query_params(
                dialog_filter.parameter_name
            )
        selected_models = DMessageModelFilter.parse_values(
            request.query_params.get("dialog_models")
        )
        return {
            "filter_reset_url": str(filter_reset_url),
            "selected_model_pills": DMessageModelFilter.display_entries(selected_models),
            "model_filter_parameter": "dialog_models",
            "model_pills_removable": bool(selected_models),
        }

    def list_query(self, request: Request) -> select:
        return select(Dialog).options(selectinload(Dialog.messages))

    def details_query(self, request: Request) -> select:
        identifier = request.path_params["pk"]
        try:
            dialog_uuid = UUID(identifier)
        except (ValueError, TypeError):
            # SQLAdmin usa el ID interno en la comprobación de borrado masivo.
            return super().details_query(request).options(selectinload(Dialog.messages))
        return select(Dialog).where(Dialog.duuid == dialog_uuid).options(selectinload(Dialog.messages))

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
    list_template = "sqladmin/dmessage_list.html"
    icon = "fa-solid fa-message"
    can_create = False

    page_size = DEFAULT_PAGE_SIZE
    page_size_options = PAGE_SIZE_OPTIONS

    column_list = [
        DMessage.dialog_id,
        DMessage.type,
        DMessage.text,
        DMessage.created_date,
    ]

    column_default_sort = (DMessage.id, True)

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
        DMessage.created_date,
    ]

    column_searchable_list = [
        DMessage.text,
    ]

    column_filters = [
        DialogUUIDFilter(
            foreign_key=DMessage.dialog_id,
            foreign_display_field=Dialog.id,
            foreign_model=Dialog,
            title="Diálogo",
            parameter_name="dialog_uuid",
        ),
        DMessageModelFilter(
            column=DMessage.model,
            title="Modelo LLM",
            parameter_name="message_models",
        ),
        DMessageTypeFilter(
            column=DMessage.type,
            title="Tipo de Mensaje",
        ),
    ]

    column_labels = {
        DMessage.id: "ID",
        DMessage.dialog_id: "UUID Diálogo",
        DMessage.type: "Tipo",
        DMessage.model: "Modelo LLM",
        DMessage.text: "Contenido",
        DMessage.usage: "Uso y Tokens (JSON)",
        DMessage.created_date: "Creado",
    }

    column_formatters = {
        DMessage.type: format_message_type,
        DMessage.dialog_id: format_message_dialog,
        DMessage.text: format_message_text,
    }

    column_formatters_detail = {
        DMessage.dialog_id: format_message_dialog,
    }

    async def list_context(self, request: Request) -> dict[str, Any]:
        filter_reset_url = request.url
        for message_filter in self.get_filters():
            filter_reset_url = filter_reset_url.remove_query_params(
                message_filter.parameter_name
            )
        base_context = {"filter_reset_url": str(filter_reset_url)}

        selected_dialog = None
        dialog_uuid_value = request.query_params.get("dialog_uuid")
        if dialog_uuid_value:
            try:
                dialog_uuid = UUID(dialog_uuid_value)
            except (ValueError, TypeError):
                dialog_uuid = None
            if dialog_uuid is not None:
                dialogs = await self._run_query(
                    select(Dialog).where(Dialog.duuid == dialog_uuid)
                )
                selected_dialog = dialogs[0] if dialogs else None

        selected_models = DMessageModelFilter.parse_values(
            request.query_params.get("message_models")
        )
        if not selected_dialog and not selected_models:
            return base_context

        pill_values = selected_models
        if not pill_values and selected_dialog:
            pill_values = [selected_dialog.model or DMessageModelFilter.NO_MODEL_VALUE]
        return {
            **base_context,
            "selected_dialog": selected_dialog,
            "selected_models": selected_models,
            "selected_model_pills": DMessageModelFilter.display_entries(pill_values),
            "model_filter_parameter": "message_models",
            "model_pills_removable": bool(selected_models),
        }

    def list_query(self, request: Request) -> select:
        return select(DMessage).options(selectinload(DMessage.dialog))

    def details_query(self, request: Request) -> select:
        return super().details_query(request).options(selectinload(DMessage.dialog))

    def sort_query(self, stmt: select, request: Request) -> select:
        if request.query_params.get("sortBy") == "created_date":
            if request.query_params.get("sort", "asc") == "desc":
                return stmt.order_by(DMessage.id.desc())
            return stmt.order_by(DMessage.id.asc())
        return super().sort_query(stmt, request)
